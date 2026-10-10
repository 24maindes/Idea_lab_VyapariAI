"""
services/supplier_stats.py - how do the shop's suppliers compare for each product?

For every (supplier, product) pair with purchases in the last N days we compute price statistics.
STABILITY = how much the price changes between purchases, measured by the coefficient of variation
(CV = standard deviation / average x 100). A supplier whose price jumps around is harder to plan with.
    CV < 3 %  -> Stable      3-7 % -> Moderate      > 7 % -> Volatile      fewer than 3 purchases -> Not enough data
BEST VALUE = the lowest average price among suppliers with at least 3 purchases that are not Volatile.
(There is deliberately NO combined "reliability score": it would hide how it was computed.)
"""
import datetime as dt
import statistics

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, Purchase, Supplier
from app.services.fair_price import _lookup, _reference_map, variance_pct

STABLE_CV_MAX = 3.0
MODERATE_CV_MAX = 7.0
MIN_PURCHASES = 3


def stability_of(count: int, cv_pct: float | None) -> str:
    if count < MIN_PURCHASES or cv_pct is None:
        return "Not enough data"
    if cv_pct < STABLE_CV_MAX:
        return "Stable"
    if cv_pct <= MODERATE_CV_MAX:
        return "Moderate"
    return "Volatile"


def supplier_stats(db: Session, shop_id: int, product_id: int | None = None, days: int = 180,
                   today: dt.date | None = None) -> list[dict]:
    today = today or dt.date.today()
    start = today - dt.timedelta(days=days)
    q = (select(Purchase, Supplier.name, Product.name, Product.reference_commodity)
         .join(Supplier, Supplier.id == Purchase.supplier_id).join(Product, Product.id == Purchase.product_id)
         .where(Purchase.shop_id == shop_id, Purchase.purchase_date >= start, Purchase.purchase_date <= today))
    if product_id is not None:
        q = q.where(Purchase.product_id == product_id)
    rows = db.execute(q.order_by(Purchase.purchase_date, Purchase.id)).all()

    maps: dict[str, dict] = {}
    groups: dict[tuple, dict] = {}
    for p, sname, pname, commodity in rows:
        if commodity and commodity not in maps:
            maps[commodity] = _reference_map(db, commodity, start, today)
        g = groups.setdefault((p.supplier_id, p.product_id), {"supplierName": sname, "productName": pname, "prices": [], "variances": [], "latest": None})
        g["prices"].append(float(p.unit_price))
        g["latest"] = float(p.unit_price)
        if commodity:
            v = variance_pct(p.unit_price, _lookup(maps[commodity], p.purchase_date))
            if v is not None:
                g["variances"].append(v)

    out = []
    for (sid, pid), g in groups.items():
        prices = g["prices"]
        avg = sum(prices) / len(prices)
        sd = statistics.pstdev(prices) if len(prices) > 1 else 0.0
        cv = (sd / avg * 100) if avg else None
        out.append({
            "supplierId": sid, "supplierName": g["supplierName"], "productId": pid, "productName": g["productName"],
            "purchaseCount": len(prices), "avgPrice": round(avg, 2), "minPrice": round(min(prices), 2), "maxPrice": round(max(prices), 2),
            "latestPrice": round(g["latest"], 2), "stdDev": round(sd, 2),
            "coefficientOfVariationPct": round(cv, 1) if cv is not None else None,
            "stability": stability_of(len(prices), cv),
            "avgVarianceVsMarketPct": round(sum(g["variances"]) / len(g["variances"]), 1) if g["variances"] else None,
            "bestValue": False,
        })

    # best value: per product, the cheapest eligible supplier
    by_product: dict[int, list[dict]] = {}
    for r in out:
        by_product.setdefault(r["productId"], []).append(r)
    for rs in by_product.values():
        eligible = [r for r in rs if r["purchaseCount"] >= MIN_PURCHASES and r["stability"] != "Volatile"]
        if eligible:
            min(eligible, key=lambda r: r["avgPrice"])["bestValue"] = True
    return sorted(out, key=lambda r: (r["productName"], r["avgPrice"]))
