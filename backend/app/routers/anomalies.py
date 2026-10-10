"""
routers/anomalies.py - alerts (price anomalies, low stock, overpaying supplier).

POST  /api/alerts/scan          scan the shop now
GET   /api/alerts               list (filters: status, severity, type, productId)
GET   /api/alerts/count         number of unread alerts (for the sidebar badge)
PATCH /api/alerts/read-all      mark everything as read
PATCH /api/alerts/{id}/read     mark one as read
Fixed routes are declared before /{id}.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import Alert, Product, Purchase, Shop, Supplier
from app.services.anomaly_service import scan_shop
from app.services.cache import invalidate_shop
from app.services.fair_price import _lookup, _reference_map, variance_pct

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("/scan")
def scan(db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    result = scan_shop(db, shop)
    invalidate_shop(shop.id)
    return result


@router.get("/count")
def count(db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    n = db.execute(select(func.count()).select_from(Alert).where(Alert.shop_id == shop.id, Alert.is_read.is_(False))).scalar()
    return {"unread": n}


@router.patch("/read-all")
def read_all(db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    res = db.execute(update(Alert).where(Alert.shop_id == shop.id, Alert.is_read.is_(False)).values(is_read=True))
    db.commit()
    invalidate_shop(shop.id)
    return {"updated": res.rowcount}


@router.patch("/{alert_id}/read")
def read_one(alert_id: int, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    alert = db.execute(select(Alert).where(Alert.id == alert_id, Alert.shop_id == shop.id)).scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    invalidate_shop(shop.id)
    return {"id": alert.id, "isRead": True}


@router.get("")
def list_alerts(
    status: Literal["all", "unread", "read"] = "all",
    severity: Literal["high", "medium", "low"] | None = None,
    type: Literal["price_anomaly", "low_stock", "overpaying"] | None = None,
    product_id: int | None = Query(None, alias="productId"),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    shop: Shop = Depends(get_current_shop),
):
    q = select(Alert).where(Alert.shop_id == shop.id)
    if status == "unread":
        q = q.where(Alert.is_read.is_(False))
    elif status == "read":
        q = q.where(Alert.is_read.is_(True))
    if severity:
        q = q.where(Alert.severity == severity)
    if type:
        q = q.where(Alert.alert_type == type)
    if product_id is not None:
        q = q.where(Alert.product_id == product_id)
    alerts = db.execute(q.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit)).scalars().all()

    products = {p.id: p for p in db.execute(select(Product).where(Product.shop_id == shop.id)).scalars()}
    purchases = {p.id: p for p in db.execute(select(Purchase).where(Purchase.id.in_([a.purchase_id for a in alerts if a.purchase_id]))).scalars()}
    suppliers = dict(db.execute(select(Supplier.id, Supplier.name).where(Supplier.shop_id == shop.id)).all())

    maps: dict[str, dict] = {}                          # reference prices, loaded once per commodity
    out = []
    for a in alerts:
        prod = products.get(a.product_id)
        pur = purchases.get(a.purchase_id)
        ref = dev = None
        if pur and prod and prod.reference_commodity:
            maps.setdefault(prod.reference_commodity, _reference_map(
                db, prod.reference_commodity, min(p.purchase_date for p in purchases.values()), max(p.purchase_date for p in purchases.values())))
            ref = _lookup(maps[prod.reference_commodity], pur.purchase_date)
            dev = variance_pct(pur.unit_price, ref)
        out.append({
            "id": a.id, "type": a.alert_type, "severity": a.severity, "message": a.message, "isRead": bool(a.is_read),
            "createdAt": a.created_at.isoformat() if a.created_at else None, "score": a.score,
            "methods": [m for m in (a.methods or "").split(",") if m],
            "productId": a.product_id, "productName": prod.name if prod else None, "unit": prod.unit if prod else None,
            "supplierName": suppliers.get(pur.supplier_id) if pur else None,
            "pricePaid": pur.unit_price if pur else None,
            "referencePrice": round(ref, 2) if ref is not None else None, "deviationPct": dev,
        })
    return out
