"""
services/fair_price.py
----------------------
Fair-price analysis: "Did I pay a fair price compared with the market?"

Idea in one line:
    variance % = (my price - market price) / market price x 100
    then a verdict from the thresholds in services/config.py.

Prices are Rs per unit (per kg / litre / packet).
"""
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Purchase, ReferencePrice, Supplier
from app.services.config import (FAIR_GREAT_DEAL_MAX, FAIR_OK_MAX, FAIR_SLIGHTLY_HIGH_MAX,
                                 REFERENCE_LOOKBACK_DAYS)


# ================================================================ small pure helpers
def variance_pct(price: float | None, ref: float | None) -> float | None:
    """
    How far above (+) or below (-) the market my price is, in percent, rounded to 1 decimal.
    Rounded on purpose: the number the shopkeeper SEES and the verdict then always agree.
    Returns None when there is no usable market price.
    """
    if price is None or ref is None or ref <= 0:
        return None
    return round((price - ref) / ref * 100, 1)


def verdict(variance: float | None) -> str | None:
    """Boundaries are inclusive on the upper side: -3 -> Great deal, 3 -> Fair, 8 -> Slightly high."""
    if variance is None:
        return None
    if variance <= FAIR_GREAT_DEAL_MAX:
        return "Great deal"
    if variance <= FAIR_OK_MAX:
        return "Fair"
    if variance <= FAIR_SLIGHTLY_HIGH_MAX:
        return "Slightly high"
    return "Overpaying"


def _rs(x: float) -> str:
    """48.0 -> '48', 47.5 -> '47.50' (short and readable in a sentence)."""
    return f"{x:.0f}" if abs(x - round(x)) < 0.005 else f"{x:.2f}"


def check_message(price: float, ref: float, variance: float, on_date: dt.date, today: dt.date) -> str:
    """Short human sentence, e.g. 'Rs 48 is 6.7% above today's market price of Rs 45'."""
    when = "today's market price" if on_date == today else "the market price"
    suffix = "" if on_date == today else f" on {on_date:%d %b %Y}"
    if variance > 0:
        return f"Rs {_rs(price)} is {abs(variance):.1f}% above {when} of Rs {_rs(ref)}{suffix}"
    if variance < 0:
        return f"Rs {_rs(price)} is {abs(variance):.1f}% below {when} of Rs {_rs(ref)}{suffix}"
    return f"Rs {_rs(price)} matches {when} of Rs {_rs(ref)}{suffix}"


# ================================================================ reference price lookup
def get_reference_price(db: Session, commodity: str | None, on_date: dt.date, kind: str = "wholesale") -> float | None:
    """
    Latest reference price on or before `on_date`, but not older than REFERENCE_LOOKBACK_DAYS.
    kind = 'wholesale' (default: what a shop pays suppliers) or 'retail'.
    """
    if not commodity:
        return None
    column = ReferencePrice.wholesale_price if kind == "wholesale" else ReferencePrice.retail_price
    row = db.execute(
        select(column)
        .where(ReferencePrice.commodity == commodity,
               ReferencePrice.price_date <= on_date,
               ReferencePrice.price_date >= on_date - dt.timedelta(days=REFERENCE_LOOKBACK_DAYS),
               column.is_not(None))
        .order_by(ReferencePrice.price_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    return float(row) if row is not None else None


def _reference_map(db: Session, commodity: str, start: dt.date, end: dt.date) -> dict[dt.date, float]:
    """
    Wholesale prices for a date range in ONE query (so analysing 26 purchases does not need 26 queries).
    Starts LOOKBACK days earlier so the first purchases can still find a price.
    """
    rows = db.execute(
        select(ReferencePrice.price_date, ReferencePrice.wholesale_price)
        .where(ReferencePrice.commodity == commodity,
               ReferencePrice.price_date >= start - dt.timedelta(days=REFERENCE_LOOKBACK_DAYS),
               ReferencePrice.price_date <= end)
        .order_by(ReferencePrice.price_date)
    ).all()
    return {d: float(p) for d, p in rows if p is not None}


def _lookup(ref_map: dict[dt.date, float], on_date: dt.date) -> float | None:
    """Same rule as get_reference_price, but on the in-memory map."""
    for back in range(REFERENCE_LOOKBACK_DAYS + 1):
        price = ref_map.get(on_date - dt.timedelta(days=back))
        if price is not None:
            return price
    return None


# ================================================================ main analysis for one product
def product_fair_price(db: Session, shop, product, days: int = 180, today: dt.date | None = None) -> dict:
    """
    Full fair-price picture for ONE product of ONE shop. Returns a dict with camelCase keys
    (the API sends it as is). Products without a linked commodity / without reference data
    return hasMarketData=False and empty market fields - never an error.
    """
    today = today or dt.date.today()
    window_start = today - dt.timedelta(days=days)
    start_90 = today - dt.timedelta(days=90)
    fetch_start = min(window_start, start_90)

    # --- purchases of this shop for this product (shop_id filter = a shop never sees another shop's data)
    purchases = db.execute(
        select(Purchase)
        .where(Purchase.shop_id == shop.id, Purchase.product_id == product.id, Purchase.purchase_date >= fetch_start)
        .order_by(Purchase.purchase_date, Purchase.id)
    ).scalars().all()

    # the very last purchase ever (may be older than the window)
    last = db.execute(
        select(Purchase)
        .where(Purchase.shop_id == shop.id, Purchase.product_id == product.id)
        .order_by(Purchase.purchase_date.desc(), Purchase.id.desc()).limit(1)
    ).scalar_one_or_none()

    supplier_names = dict(db.execute(select(Supplier.id, Supplier.name).where(Supplier.shop_id == shop.id)).all())

    commodity = getattr(product, "reference_commodity", None)
    ref_map = _reference_map(db, commodity, fetch_start, today) if commodity else {}
    has_market = bool(ref_map)

    # --- one point per purchase in the chart window
    points, supplier_acc = [], {}
    potential_savings = overspend_90 = 0.0
    for p in purchases:
        ref = _lookup(ref_map, p.purchase_date) if has_market else None
        var = variance_pct(p.unit_price, ref)
        in_window = p.purchase_date >= window_start
        if in_window:
            points.append({
                "date": p.purchase_date, "price": round(float(p.unit_price), 2),
                "supplier": supplier_names.get(p.supplier_id, "Unknown"), "supplierId": p.supplier_id,
                "quantity": float(p.quantity), "variancePct": var,
            })
            if var is not None:
                acc = supplier_acc.setdefault(p.supplier_id, {"vars": [], "qty": 0.0})
                acc["vars"].append(var)
                acc["qty"] += float(p.quantity)
        # money lost on purchases that were ABOVE the market price: (price - ref) x quantity
        if ref is not None and p.unit_price > ref:
            loss = (p.unit_price - ref) * p.quantity
            if in_window:
                potential_savings += loss
            if p.purchase_date >= start_90:
                overspend_90 += loss

    # --- last purchase vs market on the SAME date
    last_price = round(float(last.unit_price), 2) if last else None
    ref_last = _lookup(ref_map, last.purchase_date) if (last and has_market) else None
    var_last = variance_pct(last.unit_price, ref_last) if last else None

    # --- average price paid in the last 30 days, weighted by quantity (big orders count more)
    recent = [p for p in purchases if p.purchase_date >= today - dt.timedelta(days=30)]
    total_qty = sum(p.quantity for p in recent)
    avg30 = round(sum(p.unit_price * p.quantity for p in recent) / total_qty, 2) if total_qty > 0 else None

    # --- reference line for the chart
    series = [{"date": d, "referencePrice": round(v, 2)} for d, v in sorted(ref_map.items())
              if window_start <= d <= today]

    breakdown = [{
        "supplierId": sid, "supplier": supplier_names.get(sid, "Unknown"),
        "avgVariancePct": round(sum(a["vars"]) / len(a["vars"]), 1),
        "purchases": len(a["vars"]), "totalQuantity": round(a["qty"], 2),
    } for sid, a in supplier_acc.items()]
    breakdown.sort(key=lambda b: b["avgVariancePct"])

    return {
        "productId": product.id, "productName": product.name, "unit": product.unit,
        "category": getattr(product, "category", None), "referenceCommodity": commodity,
        "hasMarketData": has_market,
        "lastPurchaseDate": last.purchase_date if last else None,
        "lastPurchasePrice": last_price,
        "avg30DayPrice": avg30,
        "referencePrice": round(ref_last, 2) if ref_last is not None else None,
        "variancePct": var_last,
        "verdict": verdict(var_last),
        "potentialSavings": round(potential_savings, 2),
        "overspend90Days": round(overspend_90, 2),
        "series": series, "points": points, "supplierBreakdown": breakdown, "days": days,
    }
