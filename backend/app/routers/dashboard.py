"""
routers/dashboard.py - numbers and charts for the Dashboard page (everything is live, nothing hard-coded).

GET /api/dashboard/summary                       one call with all the cards and lists
GET /api/dashboard/price-trend?productId=&days=60   market price + forecast + the shop's own purchases
"""
import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import ActivityLog, Alert, Product, Purchase, Sale, Shop, Supplier
from app.services.cache import get_or_set
from app.services.common import get_shop_product
from app.services.decision_engine import recommend_all
from app.services.fair_price import _reference_map
from app.services.forecast_service import NoModelError, forecast_for_commodity

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _heavy_part(db: Session, shop: Shop) -> dict:
    """Recommendations + fair-price totals: the slow part, cached for 60 seconds per shop."""
    recs = recommend_all(db, shop)
    top = [{"productId": r["productId"], "productName": r["productName"], "action": r["action"], "quantity": r["quantity"],
            "unit": r["unit"], "urgency": r["urgency"], "reason": r["reasons"][0] if r["reasons"] else ""} for r in recs[:3]]

    from app.services.fair_price import product_fair_price
    products = db.execute(select(Product).where(Product.shop_id == shop.id)).scalars().all()
    over, savings = 0, 0.0
    for p in products:
        f = product_fair_price(db, shop, p)
        if f["verdict"] == "Overpaying":
            over += 1
        savings += f["overspend90Days"]
    return {"topRecommendations": top, "fairPrice": {"overpayingProducts": over, "potentialSavings90d": round(savings, 2)}}


@router.get("/summary")
def summary(db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    today = dt.date.today()
    month_start = today.replace(day=1)

    total_products = db.execute(select(func.count()).select_from(Product).where(Product.shop_id == shop.id)).scalar()
    n_suppliers = db.execute(select(func.count()).select_from(Supplier).where(Supplier.shop_id == shop.id)).scalar()
    n_purchases = db.execute(select(func.count()).select_from(Purchase).where(Purchase.shop_id == shop.id)).scalar()
    n_sales = db.execute(select(func.count()).select_from(Sale).where(Sale.shop_id == shop.id)).scalar()
    linked = db.execute(select(func.count()).select_from(Product).where(Product.shop_id == shop.id, Product.reference_commodity.is_not(None))).scalar()

    count, spend = db.execute(select(func.count(), func.coalesce(func.sum(Purchase.quantity * Purchase.unit_price), 0.0)).where(
        Purchase.shop_id == shop.id, Purchase.purchase_date >= month_start, Purchase.purchase_date <= today)).one()

    # stock units + value (value = stock x latest purchase price) with one window query
    rn = func.row_number().over(partition_by=Purchase.product_id, order_by=(Purchase.purchase_date.desc(), Purchase.id.desc())).label("rn")
    sub = select(Purchase.product_id, Purchase.unit_price, rn).where(Purchase.shop_id == shop.id).subquery()
    stock_row = db.execute(
        select(func.coalesce(func.sum(Product.current_stock), 0.0), func.coalesce(func.sum(Product.current_stock * sub.c.unit_price), 0.0))
        .select_from(Product).outerjoin(sub, (sub.c.product_id == Product.id) & (sub.c.rn == 1)).where(Product.shop_id == shop.id)).one()

    unread = db.execute(select(func.count()).select_from(Alert).where(Alert.shop_id == shop.id, Alert.is_read.is_(False))).scalar()
    low = db.execute(select(Product).where(Product.shop_id == shop.id, Product.current_stock <= Product.reorder_level)
                     .order_by(func.coalesce(Product.current_stock / func.nullif(Product.reorder_level, 0), -1).asc(), Product.name).limit(5)).scalars().all()
    activity = db.execute(select(ActivityLog).where(ActivityLog.shop_id == shop.id)
                          .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(6)).scalars().all()
    latest_alerts = db.execute(select(Alert).where(Alert.shop_id == shop.id).order_by(Alert.is_read, Alert.created_at.desc(), Alert.id.desc()).limit(3)).scalars().all()

    heavy = get_or_set(shop.id, "dashboard-heavy", 600, lambda: _heavy_part(db, shop)) if total_products else \
        {"topRecommendations": [], "fairPrice": {"overpayingProducts": 0, "potentialSavings90d": 0.0}}

    return {
        "totalProducts": total_products,
        "purchasesThisMonth": {"count": count, "spend": round(float(spend), 2)},
        "stock": {"units": round(float(stock_row[0]), 2), "value": round(float(stock_row[1]), 2)},
        "unreadAlerts": unread,
        "lowStock": [{"id": p.id, "name": p.name, "stock": p.current_stock, "unit": p.unit, "reorderLevel": p.reorder_level} for p in low],
        "topRecommendations": heavy["topRecommendations"],
        "fairPrice": heavy["fairPrice"],
        "recentActivity": [{"id": a.id, "kind": a.kind, "text": a.text, "createdAt": a.created_at.isoformat() if a.created_at else None} for a in activity],
        "latestAlerts": [{"id": a.id, "type": a.alert_type, "severity": a.severity, "message": a.message, "isRead": bool(a.is_read),
                          "createdAt": a.created_at.isoformat() if a.created_at else None} for a in latest_alerts],
        "onboarding": {"hasProducts": total_products > 0, "hasSuppliers": n_suppliers > 0, "hasPurchases": n_purchases > 0,
                       "hasSales": n_sales > 0, "hasLinkedCommodities": linked > 0},
    }


@router.get("/price-trend")
def price_trend(product_id: int = Query(..., alias="productId"), days: int = Query(60, ge=7, le=365),
                db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    product = get_shop_product(db, shop.id, product_id)

    def build() -> dict:
        today = dt.date.today()
        start = today - dt.timedelta(days=days)
        history, forecast = [], []
        if product.reference_commodity:
            ref = _reference_map(db, product.reference_commodity, start, today)
            history = [{"date": d.isoformat(), "marketPrice": round(v, 2)} for d, v in sorted(ref.items()) if d >= start]
            try:
                forecast = forecast_for_commodity(db, product.reference_commodity, 7)["forecast"]
            except NoModelError:
                forecast = []
        rows = db.execute(select(Purchase.purchase_date, Purchase.unit_price, Supplier.name)
                          .outerjoin(Supplier, Supplier.id == Purchase.supplier_id)
                          .where(Purchase.shop_id == shop.id, Purchase.product_id == product.id, Purchase.purchase_date >= start)
                          .order_by(Purchase.purchase_date, Purchase.id)).all()
        return {"productId": product.id, "productName": product.name, "unit": product.unit, "commodity": product.reference_commodity,
                "history": history, "forecast": forecast,
                "purchases": [{"date": d.isoformat(), "price": round(float(p), 2), "supplier": s or "Unknown"} for d, p, s in rows]}

    return get_or_set(shop.id, ("trend", product.id, days), 300, build)
