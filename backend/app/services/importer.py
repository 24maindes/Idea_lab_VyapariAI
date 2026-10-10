"""
services/importer.py - bulk import of products, purchases and sales from a CSV file.

TWO STEPS (so a real import can never half-succeed):
  1. validate_*  : check EVERY row and return a list of errors (row number, field, message). Nothing is written.
  2. apply_*     : only called when the file is valid (or skipInvalid=true) - writes the rows in ONE transaction.
A "dry run" does step 1 only.

Row numbers are spreadsheet row numbers: the header is row 1, the first data row is row 2.
"""
import csv
import datetime as dt
import io

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, Purchase, Sale, Shop, Supplier
from app.services.common import commodity_exists

MAX_BYTES = 5 * 1024 * 1024
UNITS = {"kg", "litre", "packet", "box"}

COLUMNS = {
    "products": ["name", "category", "unit", "opening_stock", "reorder_level", "selling_price", "reference_commodity"],
    "purchases": ["date", "product", "supplier", "quantity", "unit_price"],
    "sales": ["date", "product", "quantity", "unit_price"],
}
REQUIRED = {
    "products": ["name", "unit"],
    "purchases": ["date", "product", "supplier", "quantity", "unit_price"],
    "sales": ["date", "product", "quantity", "unit_price"],
}
SAMPLES = {
    "products": [["Rice", "Grains", "kg", "50", "20", "48", "Rice"], ["Toor Dal", "Pulses", "kg", "25", "10", "135", "Toor Dal"]],
    "purchases": [["2026-09-01", "Rice", "ABC Traders", "40", "41.5"], ["2026-09-08", "Rice", "ABC Traders", "40", "42"]],
    "sales": [["2026-09-02", "Rice", "5", "48"], ["2026-09-03", "Rice", "4.5", "48"]],
}


# ---------------------------------------------------------------- reading the file
def read_csv(raw: bytes, kind: str) -> list[tuple[int, dict]]:
    """Bytes -> [(row_number, {column: text})]. Handles the UTF-8 BOM that Excel adds."""
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File is too large (maximum 5 MB)")
    if not raw.strip():
        raise HTTPException(status_code=422, detail="The file is empty")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="The file must be a UTF-8 CSV (in Excel: Save As > CSV UTF-8)")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="The file has no header row")
    header = [(h or "").strip().lower().replace(" ", "_") for h in reader.fieldnames]
    missing = [c for c in REQUIRED[kind] if c not in header]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing column(s): {', '.join(missing)}. Expected: {', '.join(COLUMNS[kind])}")
    reader.fieldnames = header
    rows = []
    for i, row in enumerate(reader, start=2):
        clean = {k: (v or "").strip() for k, v in row.items() if k}
        if any(clean.values()):                              # skip completely blank lines
            rows.append((i, clean))
    if not rows:
        raise HTTPException(status_code=422, detail="The file has a header but no data rows")
    return rows


def _number(value: str):
    return float(value.replace(",", ""))


class Errors(list):
    def add(self, row: int, field: str, message: str) -> None:
        self.append({"row": row, "field": field, "message": message})


def _parse_number(row, field, rec, errors, *, required=True, minimum=None, strictly_positive=False):
    raw = rec.get(field, "")
    if raw == "":
        if required:
            errors.add(row, field, f"{field} is required")
        return None
    try:
        v = _number(raw)
    except ValueError:
        errors.add(row, field, f"{field} must be a number (got '{raw}')")
        return None
    if strictly_positive and v <= 0:
        errors.add(row, field, f"{field} must be greater than 0")
        return None
    if minimum is not None and v < minimum:
        errors.add(row, field, f"{field} cannot be negative")
        return None
    return v


def _parse_date(row, rec, errors):
    raw = rec.get("date", "")
    if raw == "":
        errors.add(row, "date", "date is required")
        return None
    try:
        d = dt.date.fromisoformat(raw)
    except ValueError:
        errors.add(row, "date", f"date must look like 2026-09-30 (got '{raw}')")
        return None
    if d > dt.date.today():
        errors.add(row, "date", "date cannot be in the future")
        return None
    return d


# ---------------------------------------------------------------- products
def validate_products(db: Session, shop: Shop, rows) -> tuple[list[dict], Errors]:
    errors, good = Errors(), []
    existing = {n.lower() for (n,) in db.execute(select(Product.name).where(Product.shop_id == shop.id))}
    seen: dict[str, int] = {}
    for row, rec in rows:
        before = len(errors)
        name = rec.get("name", "")
        if not name:
            errors.add(row, "name", "name is required")
        elif len(name) > 120:
            errors.add(row, "name", "name is too long (maximum 120 characters)")
        unit = rec.get("unit", "").lower()
        if not unit:
            errors.add(row, "unit", "unit is required")
        elif unit not in UNITS:
            errors.add(row, "unit", f"unit must be one of {', '.join(sorted(UNITS))} (got '{rec['unit']}')")
        opening = _parse_number(row, "opening_stock", rec, errors, required=False, minimum=0)
        reorder = _parse_number(row, "reorder_level", rec, errors, required=False, minimum=0)
        price = _parse_number(row, "selling_price", rec, errors, required=False, strictly_positive=True)
        commodity = rec.get("reference_commodity", "") or None
        if commodity and not commodity_exists(db, commodity):
            errors.add(row, "reference_commodity", f"unknown commodity '{commodity}'")
        if name:
            key = name.lower()
            if key in existing:
                errors.add(row, "name", f"product '{name}' already exists")
            elif key in seen:
                errors.add(row, "name", f"duplicate of row {seen[key]}")
            else:
                seen[key] = row
        if len(errors) == before:
            good.append({"row": row, "name": name, "category": rec.get("category") or None, "unit": unit,
                         "opening": opening or 0.0, "reorder": reorder or 0.0, "price": price, "commodity": commodity})
    return good, errors


def apply_products(db: Session, shop: Shop, good: list[dict]) -> dict:
    for g in good:
        db.add(Product(shop_id=shop.id, name=g["name"], category=g["category"], unit=g["unit"], current_stock=g["opening"],
                       reorder_level=g["reorder"], selling_price=g["price"], reference_commodity=g["commodity"]))
    return {"products": len(good)}


# ---------------------------------------------------------------- purchases
def validate_purchases(db: Session, shop: Shop, rows, create_missing_suppliers: bool) -> tuple[list[dict], Errors, set[str]]:
    errors, good, new_suppliers = Errors(), [], set()
    products = {p.name.lower(): p for p in db.execute(select(Product).where(Product.shop_id == shop.id)).scalars()}
    suppliers = {s.name.lower(): s for s in db.execute(select(Supplier).where(Supplier.shop_id == shop.id)).scalars()}
    seen: dict[tuple, int] = {}
    for row, rec in rows:
        before = len(errors)
        d = _parse_date(row, rec, errors)
        pname, sname = rec.get("product", ""), rec.get("supplier", "")
        product = products.get(pname.lower()) if pname else None
        if not pname:
            errors.add(row, "product", "product is required")
        elif product is None:
            errors.add(row, "product", f"unknown product '{pname}' (add it first or fix the spelling)")
        supplier = suppliers.get(sname.lower()) if sname else None
        if not sname:
            errors.add(row, "supplier", "supplier is required")
        elif supplier is None:
            if create_missing_suppliers:
                new_suppliers.add(sname)
            else:
                errors.add(row, "supplier", f"unknown supplier '{sname}' (tick 'create missing suppliers' to add it automatically)")
        qty = _parse_number(row, "quantity", rec, errors, strictly_positive=True)
        price = _parse_number(row, "unit_price", rec, errors, strictly_positive=True)
        if d and product and sname and qty and price:
            key = (d, pname.lower(), sname.lower(), qty, price)
            if key in seen:
                errors.add(row, "row", f"duplicate of row {seen[key]}")
            else:
                seen[key] = row
        if len(errors) == before:
            good.append({"row": row, "date": d, "product": product, "supplierName": sname, "supplier": supplier, "qty": qty, "price": price})
    return good, errors, {n for n in new_suppliers}


def apply_purchases(db: Session, shop: Shop, good: list[dict]) -> dict:
    created_suppliers: dict[str, Supplier] = {}
    for g in good:
        supplier = g["supplier"]
        if supplier is None:
            key = g["supplierName"].lower()
            if key not in created_suppliers:
                created_suppliers[key] = Supplier(shop_id=shop.id, name=g["supplierName"])
                db.add(created_suppliers[key])
                db.flush()
            supplier = created_suppliers[key]
        db.add(Purchase(shop_id=shop.id, product_id=g["product"].id, supplier_id=supplier.id, quantity=g["qty"],
                        unit_price=g["price"], purchase_date=g["date"]))
        g["product"].current_stock = round(g["product"].current_stock + g["qty"], 6)
    return {"purchases": len(good), "suppliers": len(created_suppliers)}


# ---------------------------------------------------------------- sales
def validate_sales(db: Session, shop: Shop, rows) -> tuple[list[dict], Errors]:
    """Rows are checked in DATE ORDER while a running stock is kept, so a sale is only valid if stock was there on that day."""
    errors, good = Errors(), []
    products = {p.name.lower(): p for p in db.execute(select(Product).where(Product.shop_id == shop.id)).scalars()}
    running = {p.id: p.current_stock for p in products.values()}
    seen: dict[tuple, int] = {}

    parsed = []
    for row, rec in rows:
        before = len(errors)
        d = _parse_date(row, rec, errors)
        pname = rec.get("product", "")
        product = products.get(pname.lower()) if pname else None
        if not pname:
            errors.add(row, "product", "product is required")
        elif product is None:
            errors.add(row, "product", f"unknown product '{pname}'")
        qty = _parse_number(row, "quantity", rec, errors, strictly_positive=True)
        price = _parse_number(row, "unit_price", rec, errors, strictly_positive=True)
        if d and product and qty and price:
            key = (d, pname.lower(), qty, price)
            if key in seen:
                errors.add(row, "row", f"duplicate of row {seen[key]}")
            else:
                seen[key] = row
        if len(errors) == before:
            parsed.append({"row": row, "date": d, "product": product, "qty": qty, "price": price})

    for g in sorted(parsed, key=lambda x: (x["date"], x["row"])):          # chronological
        available = running[g["product"].id]
        if g["qty"] > available + 1e-9:
            errors.add(g["row"], "quantity", f"would push {g['product'].name} stock below zero (only {available:g} {g['product'].unit} available on {g['date']})")
        else:
            running[g["product"].id] = available - g["qty"]
            good.append(g)
    errors.sort(key=lambda e: e["row"])
    return good, errors


def apply_sales(db: Session, shop: Shop, good: list[dict]) -> dict:
    for g in good:
        db.add(Sale(shop_id=shop.id, product_id=g["product"].id, quantity=g["qty"], unit_price=g["price"], sale_date=g["date"]))
        g["product"].current_stock = round(g["product"].current_stock - g["qty"], 6)
    return {"sales": len(good)}


def template_csv(kind: str) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(COLUMNS[kind])
    w.writerows(SAMPLES[kind])
    return out.getvalue()
