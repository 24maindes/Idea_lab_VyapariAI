"""
routers/suppliers.py - suppliers of the logged-in shop (CRUD) + which products each one supplies.

GET    /api/suppliers          list
POST   /api/suppliers          create
PUT    /api/suppliers/{id}     update (productIds replaces the whole list)
DELETE /api/suppliers/{id}     409 if the supplier has purchases

NOTE: more specific routes (e.g. /comparison, added later) must be declared BEFORE /{id}.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import Product, Purchase, Shop, Supplier, supplier_products
from app.schemas import SupplierIn, SupplierOut
from app.services.activity import log_activity
from app.services.common import get_shop_product, get_shop_supplier
from app.services.supplier_stats import supplier_stats
from app.services.fair_price import _lookup, _reference_map
import datetime as dt
from fastapi import Query

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def _links(db: Session, supplier_ids: list[int]) -> dict[int, list[tuple[int, str]]]:
    """supplier_id -> [(product_id, product_name), ...] in ONE query."""
    out: dict[int, list[tuple[int, str]]] = {sid: [] for sid in supplier_ids}
    if not supplier_ids:
        return out
    rows = db.execute(
        select(supplier_products.c.supplier_id, Product.id, Product.name)
        .join(Product, Product.id == supplier_products.c.product_id)
        .where(supplier_products.c.supplier_id.in_(supplier_ids))
        .order_by(Product.name)
    ).all()
    for sid, pid, pname in rows:
        out[sid].append((pid, pname))
    return out


def to_out(s: Supplier, links: list[tuple[int, str]]) -> dict:
    return {"id": s.id, "name": s.name, "contact": s.contact, "address": s.address,
            "product_ids": [p[0] for p in links], "product_names": [p[1] for p in links]}


def _valid_product_ids(db: Session, shop_id: int, ids: list[int]) -> list[int]:
    ids = list(dict.fromkeys(ids))                              # remove duplicates, keep order
    if not ids:
        return []
    found = set(db.execute(select(Product.id).where(Product.shop_id == shop_id, Product.id.in_(ids))).scalars())
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(status_code=422, detail=f"Unknown product id(s): {missing}")
    return ids


def _check_name_free(db: Session, shop_id: int, name: str, exclude_id: int | None = None) -> None:
    q = select(Supplier.id).where(Supplier.shop_id == shop_id, func.lower(Supplier.name) == name.strip().lower())
    if exclude_id is not None:
        q = q.where(Supplier.id != exclude_id)
    if db.execute(q).first() is not None:
        raise HTTPException(status_code=409, detail="A supplier with this name already exists")


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    suppliers = db.execute(select(Supplier).where(Supplier.shop_id == shop.id).order_by(Supplier.name)).scalars().all()
    links = _links(db, [s.id for s in suppliers])
    return [to_out(s, links[s.id]) for s in suppliers]


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(payload: SupplierIn, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Supplier name is required")
    _check_name_free(db, shop.id, name)
    ids = _valid_product_ids(db, shop.id, payload.product_ids)
    s = Supplier(shop_id=shop.id, name=name, contact=(payload.contact or "").strip() or None,
                 address=(payload.address or "").strip() or None)
    db.add(s)
    db.flush()
    if ids:
        db.execute(supplier_products.insert(), [{"supplier_id": s.id, "product_id": i} for i in ids])
    log_activity(db, shop.id, "supplier", f"Supplier added - {s.name}")
    db.commit()
    return to_out(s, _links(db, [s.id])[s.id])


@router.get("/comparison")
def comparison(product_id: int = Query(..., alias="productId"), days: int = Query(180, ge=7, le=730),
               db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    """Suppliers compared for ONE product: average price, stability, variance vs market, best value."""
    product = get_shop_product(db, shop.id, product_id)
    stats = supplier_stats(db, shop.id, product.id, days)
    market_avg = None
    if product.reference_commodity:
        ref = _reference_map(db, product.reference_commodity, dt.date.today() - dt.timedelta(days=days), dt.date.today())
        vals = [v for d, v in ref.items() if d >= dt.date.today() - dt.timedelta(days=days)]
        market_avg = round(sum(vals) / len(vals), 2) if vals else None
    return {"productId": product.id, "productName": product.name, "unit": product.unit, "marketAvgPrice": market_avg,
            "suppliers": sorted(stats, key=lambda r: r["avgPrice"])}


@router.get("/{supplier_id}/prices")
def supplier_prices(supplier_id: int, product_id: int = Query(..., alias="productId"), days: int = Query(180, ge=7, le=730),
                    db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    """Price history of one supplier for one product, plus the market (reference) price series for the same period."""
    s = get_shop_supplier(db, shop.id, supplier_id)
    product = get_shop_product(db, shop.id, product_id)
    start = dt.date.today() - dt.timedelta(days=days)
    rows = db.execute(select(Purchase.purchase_date, Purchase.unit_price).where(
        Purchase.shop_id == shop.id, Purchase.supplier_id == s.id, Purchase.product_id == product.id, Purchase.purchase_date >= start)
        .order_by(Purchase.purchase_date, Purchase.id)).all()
    ref = _reference_map(db, product.reference_commodity, start, dt.date.today()) if product.reference_commodity else {}
    return {"supplierId": s.id, "supplierName": s.name, "productId": product.id, "productName": product.name, "unit": product.unit,
            "prices": [{"date": d.isoformat(), "price": round(float(p), 2)} for d, p in rows],
            "reference": [{"date": d.isoformat(), "price": round(v, 2)} for d, v in sorted(ref.items()) if d >= start]}


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, payload: SupplierIn, db: Session = Depends(get_db),
                    shop: Shop = Depends(get_current_shop)):
    s = get_shop_supplier(db, shop.id, supplier_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Supplier name is required")
    _check_name_free(db, shop.id, name, exclude_id=s.id)
    ids = _valid_product_ids(db, shop.id, payload.product_ids)
    s.name = name
    s.contact = (payload.contact or "").strip() or None
    s.address = (payload.address or "").strip() or None
    db.execute(delete(supplier_products).where(supplier_products.c.supplier_id == s.id))
    if ids:
        db.execute(supplier_products.insert(), [{"supplier_id": s.id, "product_id": i} for i in ids])
    db.commit()
    return to_out(s, _links(db, [s.id])[s.id])


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    s = get_shop_supplier(db, shop.id, supplier_id)
    if db.execute(select(func.count()).select_from(Purchase).where(Purchase.supplier_id == s.id)).scalar():
        raise HTTPException(status_code=409, detail="Supplier has purchases and cannot be deleted")
    db.execute(delete(supplier_products).where(supplier_products.c.supplier_id == s.id))
    db.delete(s)
    db.commit()
