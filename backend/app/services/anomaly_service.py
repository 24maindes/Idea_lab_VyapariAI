"""
services/anomaly_service.py - uses ml/anomaly.py on a shop's real purchases and writes Alert rows.

scan_shop(db, shop)        scan every purchase + low-stock + "overpaying supplier" checks (safe to run many times)
check_purchase(db, purchase)  quick check of ONE new purchase (called right after it is saved)

Thresholds come from the Shop row (z_cutoff, anomaly_threshold_pct), so the shopkeeper can tune them in Settings.
"""
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import anomaly as ml
from app.models import Alert, Product, Purchase, Shop, Supplier
from app.services.config import OVERPAYING_PCT
from app.services.fair_price import _lookup, _reference_map, variance_pct
from app.services.common import fmt_qty


# ---------------------------------------------------------------- building the input table
def _purchase_frame(db: Session, shop_id: int, product_id: int | None = None, upto: Purchase | None = None) -> pd.DataFrame:
    """One row per purchase with the market (reference) price of that day. NaN when no market price is known."""
    q = select(Purchase).where(Purchase.shop_id == shop_id)
    if product_id is not None:
        q = q.where(Purchase.product_id == product_id)
    purchases = db.execute(q.order_by(Purchase.purchase_date, Purchase.id)).scalars().all()
    if upto is not None:                                     # never look at purchases after the one being checked
        purchases = [p for p in purchases if (p.purchase_date, p.id) <= (upto.purchase_date, upto.id)]
    if not purchases:
        return pd.DataFrame(columns=["purchase_id", "product_id", "purchase_date", "unit_price", "reference_price"])

    commodity = dict(db.execute(select(Product.id, Product.reference_commodity).where(Product.shop_id == shop_id)).all())
    lo, hi = min(p.purchase_date for p in purchases), max(p.purchase_date for p in purchases)
    maps = {c: _reference_map(db, c, lo, hi) for c in {commodity.get(p.product_id) for p in purchases} if c}

    rows = []
    for p in purchases:
        c = commodity.get(p.product_id)
        ref = _lookup(maps[c], p.purchase_date) if c in maps else None
        rows.append({"purchase_id": p.id, "product_id": p.product_id, "purchase_date": p.purchase_date,
                     "unit_price": float(p.unit_price), "reference_price": ref if ref is not None else float("nan")})
    return pd.DataFrame(rows)


def _message(product: Product, price: float, supplier_name: str | None, deviation: float, ref: float | None,
             methods: list[str]) -> str:
    unit = product.unit
    who = f" from {supplier_name}" if supplier_name else ""
    way = "above" if deviation >= 0 else "below"
    basis = f"the market price of Rs {ref:g}" if ref and ref == ref else "its recent normal price"
    labels = ", ".join(ml.METHOD_LABELS[m] for m in methods) or "large deviation"
    return (f"{product.name} bought at Rs {price:g}/{unit}{who} is {abs(deviation):.0f}% {way} {basis} "
            f"(flagged by {labels})")


# ---------------------------------------------------------------- full scan
def scan_shop(db: Session, shop: Shop) -> dict:
    products = {p.id: p for p in db.execute(select(Product).where(Product.shop_id == shop.id)).scalars()}
    suppliers = dict(db.execute(select(Supplier.id, Supplier.name).where(Supplier.shop_id == shop.id)).all())
    purchases = {p.id: p for p in db.execute(select(Purchase).where(Purchase.shop_id == shop.id)).scalars()}

    created = {"price_anomaly": 0, "low_stock": 0, "overpaying": 0}

    # ---- 1. price anomalies
    df = _purchase_frame(db, shop.id)
    if len(df):
        feats = ml.build_features(df)
        res = ml.ensemble(feats, cutoff=shop.z_cutoff, threshold_pct=shop.anomaly_threshold_pct)
        existing = set(db.execute(select(Alert.purchase_id).where(Alert.shop_id == shop.id, Alert.alert_type == "price_anomaly")).scalars())
        for i in res.index[res["flagged"]]:
            pid = int(res.at[i, "purchase_id"])
            if pid in existing:
                continue                                     # never duplicate an alert
            p = purchases[pid]
            ref = feats.at[i, "reference_price"]
            db.add(Alert(shop_id=shop.id, product_id=p.product_id, purchase_id=pid, alert_type="price_anomaly",
                         severity=res.at[i, "severity"], methods=",".join(res.at[i, "methods"]), score=float(res.at[i, "score"]),
                         message=_message(products[p.product_id], p.unit_price, suppliers.get(p.supplier_id),
                                          float(res.at[i, "deviationPct"]), ref, res.at[i, "methods"])))
            created["price_anomaly"] += 1

    # ---- 2. low stock: one UNREAD alert per product; alerts of recovered products are closed
    unread_low = {a.product_id: a for a in db.execute(select(Alert).where(
        Alert.shop_id == shop.id, Alert.alert_type == "low_stock", Alert.is_read.is_(False))).scalars()}
    for prod in products.values():
        low = prod.current_stock <= prod.reorder_level
        if low and prod.id not in unread_low:
            left = "out of stock" if prod.current_stock <= 0 else f"only {fmt_qty(prod.current_stock)} {prod.unit} left"
            db.add(Alert(shop_id=shop.id, product_id=prod.id, alert_type="low_stock",
                         severity="high" if prod.current_stock <= 0 else "medium", score=0.0,
                         message=f"{prod.name} is {left} (reorder level {fmt_qty(prod.reorder_level)} {prod.unit})"))
            created["low_stock"] += 1
        elif not low and prod.id in unread_low:
            unread_low[prod.id].is_read = True

    # ---- 3. overpaying supplier: last 3 purchases of a product from one supplier all > 8 % above market
    if len(df):
        ref_by_purchase = df.set_index("purchase_id")["reference_price"].to_dict()
        groups: dict[tuple, list[Purchase]] = {}
        for p in sorted(purchases.values(), key=lambda x: (x.purchase_date, x.id)):
            groups.setdefault((p.product_id, p.supplier_id), []).append(p)
        existing_over = set(db.execute(select(Alert.purchase_id).where(Alert.shop_id == shop.id, Alert.alert_type == "overpaying")).scalars())
        for (product_id, supplier_id), plist in groups.items():
            last3 = plist[-3:]
            if len(last3) < 3 or last3[-1].id in existing_over:
                continue
            devs = [variance_pct(p.unit_price, ref_by_purchase.get(p.id)) for p in last3]
            if all(d is not None and d > OVERPAYING_PCT for d in devs):
                prod = products[product_id]
                db.add(Alert(shop_id=shop.id, product_id=product_id, purchase_id=last3[-1].id, alert_type="overpaying",
                             severity="medium", score=0.0, message=(
                                 f"{suppliers.get(supplier_id, 'A supplier')} charged more than {OVERPAYING_PCT}% above the market price "
                                 f"on the last 3 {prod.name} purchases (average +{sum(devs) / 3:.0f}%). Compare other suppliers.")))
                created["overpaying"] += 1

    db.commit()
    return {"created": created, "newAlerts": sum(created.values()), "purchasesScanned": len(df)}


# ---------------------------------------------------------------- one purchase
def check_purchase(db: Session, purchase: Purchase) -> dict | None:
    """
    Check ONE new purchase using the product's earlier purchases. Returns None when normal, else
    {severity, message, deviationPct, methods}; the Alert row is added to the session (the caller commits).
    """
    shop = db.get(Shop, purchase.shop_id)
    df = _purchase_frame(db, purchase.shop_id, purchase.product_id, upto=purchase)
    if df.empty:
        return None
    feats = ml.build_features(df)
    res = ml.ensemble(feats, cutoff=shop.z_cutoff, threshold_pct=shop.anomaly_threshold_pct)
    row = res.index[res["purchase_id"] == purchase.id]
    if len(row) == 0 or not bool(res.at[row[0], "flagged"]):
        return None
    i = row[0]
    product = db.get(Product, purchase.product_id)
    supplier = db.get(Supplier, purchase.supplier_id) if purchase.supplier_id else None
    dev, methods, severity = float(res.at[i, "deviationPct"]), res.at[i, "methods"], res.at[i, "severity"]
    message = _message(product, purchase.unit_price, supplier.name if supplier else None, dev, feats.at[i, "reference_price"], methods)
    already = db.execute(select(Alert.id).where(Alert.purchase_id == purchase.id, Alert.alert_type == "price_anomaly")).first()
    if already is None:
        db.add(Alert(shop_id=purchase.shop_id, product_id=purchase.product_id, purchase_id=purchase.id, alert_type="price_anomaly",
                     severity=severity, methods=",".join(methods), score=float(res.at[i, "score"]), message=message))
    return {"severity": severity, "message": message, "deviationPct": dev, "methods": methods, "direction": res.at[i, "direction"]}
