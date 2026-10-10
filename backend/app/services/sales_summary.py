"""
services/sales_summary.py - sales totals and per-product sales statistics.

get_sales_summary(db, shop_id, days) is imported by other services (inventory, decision engine,
dashboard, advisor), so the field names below must not change.
"""
import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product, Purchase, Sale


def weighted_avg_cost(db: Session, shop_id: int, product_ids: list[int], last_n: int = 5) -> dict[int, float]:
    """product_id -> quantity-weighted average unit price of its last N purchases (missing = no purchases)."""
    if not product_ids:
        return {}
    rn = func.row_number().over(partition_by=Purchase.product_id,
                                order_by=(Purchase.purchase_date.desc(), Purchase.id.desc())).label("rn")
    sub = (select(Purchase.product_id, Purchase.quantity, Purchase.unit_price, rn)
           .where(Purchase.shop_id == shop_id, Purchase.product_id.in_(product_ids)).subquery())
    rows = db.execute(select(sub.c.product_id, sub.c.quantity, sub.c.unit_price).where(sub.c.rn <= last_n)).all()
    qty: dict[int, float] = {}
    value: dict[int, float] = {}
    for pid, q, price in rows:
        qty[pid] = qty.get(pid, 0.0) + q
        value[pid] = value.get(pid, 0.0) + q * price
    return {pid: value[pid] / qty[pid] for pid in qty if qty[pid] > 0}


def _totals(db: Session, shop_id: int, start: dt.date, end: dt.date) -> dict:
    revenue, units = db.execute(
        select(func.coalesce(func.sum(Sale.quantity * Sale.unit_price), 0.0), func.coalesce(func.sum(Sale.quantity), 0.0))
        .where(Sale.shop_id == shop_id, Sale.sale_date >= start, Sale.sale_date <= end)
    ).one()
    return {"revenue": round(float(revenue), 2), "units": round(float(units), 2)}


def get_sales_summary(db: Session, shop_id: int, days: int = 30, today: dt.date | None = None) -> dict:
    """
    {totals: {today, last7Days, last30Days: {revenue, units}},
     products: [{productId, productName, qtySold, revenue, avgDailySales, grossProfit}]}

    avgDailySales = qtySold / min(days, days since the product's first sale in the window, at least 1).
    (A product first sold 5 days ago is divided by 6 days, not by the whole 30, otherwise new products
    would look like they sell very little.)
    grossProfit = revenue - qtySold x weighted-average unit cost of the product's last 5 purchases.
    """
    today = today or dt.date.today()
    window_start = today - dt.timedelta(days=days - 1)

    totals = {
        "today": _totals(db, shop_id, today, today),
        "last7Days": _totals(db, shop_id, today - dt.timedelta(days=6), today),
        "last30Days": _totals(db, shop_id, today - dt.timedelta(days=29), today),
    }

    rows = db.execute(
        select(Sale.product_id, Product.name, func.sum(Sale.quantity), func.sum(Sale.quantity * Sale.unit_price),
               func.min(Sale.sale_date))
        .join(Product, Product.id == Sale.product_id)
        .where(Sale.shop_id == shop_id, Sale.sale_date >= window_start, Sale.sale_date <= today)
        .group_by(Sale.product_id, Product.name)
        .order_by(Product.name)
    ).all()

    costs = weighted_avg_cost(db, shop_id, [r[0] for r in rows])
    products = []
    for pid, name, qty, revenue, first_sale in rows:
        effective_days = max(1, min(days, (today - first_sale).days + 1))
        cost = costs.get(pid, 0.0)                              # 0 cost if the product has no purchases
        products.append({
            "productId": pid, "productName": name,
            "qtySold": round(float(qty), 2), "revenue": round(float(revenue), 2),
            "avgDailySales": round(float(qty) / effective_days, 3),
            "grossProfit": round(float(revenue) - float(qty) * cost, 2),
        })
    return {"totals": totals, "products": products}
