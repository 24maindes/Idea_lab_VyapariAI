"""
services/decision_engine.py - the Purchase Decision Engine: Buy Now / Buy Limited / Wait + quantity.

Two layers:
  decide(inputs)               PURE function (numbers in, decision out). Easy to test and to explain.
  recommend_for_product / recommend_all   gather the inputs from the database, then call decide().

THE RULES (first match wins):
  derived numbers
    days_left     = stock / average daily sales                     how long the stock lasts
    need_lead     = avg daily sales x supplier lead time            what we will sell while waiting for delivery
    target_stock  = avg daily sales x cover days                    what we want on the shelf
    shortfall     = max(0, target_stock - stock)                    what is missing
  1. stock <= need_lead                    -> Buy Now (shortfall).  If the price is bad (overpaying / anomaly): Buy Limited
                                              (need_lead x 1.2) and compare suppliers first.
  2. forecast Rising (>= +3 %) and days_left < cover_days -> Buy Now (shortfall; x1.2 if rise >= 6 %): buy before it costs more
  3. forecast Falling (<= -3 %) and days_left >= lead time + 2 -> Wait 3 days: stock is enough, price is dropping
  4. price is bad (overpaying / anomaly)   -> Buy Limited (50 % of shortfall)
  5. days_left >= cover_days               -> Wait 5 days: enough stock
  6. otherwise                             -> Buy Limited (50 % of shortfall): top up carefully
NO SALES HISTORY: we cannot know the sales speed, so we use the reorder level: need_lead = reorder level,
target = reorder level x 3 (and the implied speed = reorder level / lead time).
"""
import datetime as dt
import math

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Alert, Product, Purchase, Shop, Supplier
from app.services import config as C
from app.services.cache import ttl_cache
from app.services.common import fmt_qty
from app.services.fair_price import product_fair_price
from app.services.forecast_service import NoModelError, forecast_for_commodity
from app.services.sales_summary import get_sales_summary

BAD_VERDICTS = ("Overpaying",)


def round_qty(x: float, unit: str | None) -> float:
    """Round UP to a sensible size: whole numbers for packets/boxes, one decimal for kg/litre."""
    if x <= 0:
        return 0
    if unit in ("packet", "box"):
        return float(math.ceil(x - 1e-9))
    return math.ceil(x * 10 - 1e-9) / 10


def confidence_of(mape: float | None) -> str:
    if mape is None:
        return "Low"
    if mape < C.DECISION_CONFIDENCE_HIGH_MAPE:
        return "High"
    if mape < C.DECISION_CONFIDENCE_MEDIUM_MAPE:
        return "Medium"
    return "Low"


def decide(i: dict) -> dict:
    """
    inputs: stock, unit, avg_daily_sales (None/0 = no history), reorder_level, lead_time_days, cover_days,
            change_pct (None = no forecast), direction ('Rising'/'Falling'/'Stable'), verdict, anomaly (bool), mape
    """
    stock = float(i["stock"])
    unit = i.get("unit")
    lead, cover = int(i["lead_time_days"]), int(i["cover_days"])
    change = i.get("change_pct")
    direction = i.get("direction") or "Stable"
    bad_price = i.get("verdict") in BAD_VERDICTS or bool(i.get("anomaly"))
    notes: list[str] = []
    reasons: list[str] = []

    # ---- derived numbers (with the no-sales fallback)
    avg = i.get("avg_daily_sales") or 0.0
    reorder = float(i.get("reorder_level") or 0)
    if avg > 0:
        need_lead, target = avg * lead, avg * cover
        days_left = stock / avg
    elif reorder > 0:
        notes.append("No sales history - using reorder level")
        need_lead, target = reorder, reorder * C.DECISION_NO_SALES_COVER_MULT
        days_left = stock / (reorder / max(lead, 1))               # implied speed: reorder level lasts one lead time
    else:
        out = _result("Wait", 0, 3, ["There is no sales history and no reorder level, so an order size cannot be worked out. "
                                     "Record some sales or set a reorder level."], None, None, i, ["No sales history and no reorder level"])
        out["checkAgainInDays"] = C.DECISION_CHECK_ENOUGH_DAYS
        return out
    shortfall = max(0.0, target - stock)

    if change is None:
        notes.append("No price forecast available - treating the price direction as Stable")
        direction = "Stable"

    def note_price() -> str:
        if i.get("verdict") == "Overpaying":
            return f"your last price was well above the market ({i.get('variance_pct'):+.1f}%)" if i.get("variance_pct") is not None else "your last price was well above the market"
        return "your latest purchase price looks abnormal"

    # ---- 1. stockout risk
    if stock <= need_lead:
        base = (f"Stock is {fmt_qty(stock)} {unit}, which is at or below what you will sell during the {lead}-day "
                f"delivery time ({fmt_qty(round(need_lead, 1))} {unit}).")
        if bad_price:
            qty = round_qty(need_lead * C.DECISION_STOCKOUT_LIMITED_MULT, unit)
            reasons += [base, f"But {note_price()}, so buy only {fmt_qty(qty)} {unit} to cover the delivery time and compare suppliers first."]
            return _result("Buy Limited", qty, 1, reasons, days_left, None, i, notes)
        qty = round_qty(shortfall, unit) or round_qty(need_lead, unit)
        reasons += [base, f"Order {fmt_qty(qty)} {unit} to reach your {cover}-day target stock of {fmt_qty(round(target, 1))} {unit}."]
        return _result("Buy Now", qty, 1, reasons, days_left, None, i, notes)

    # ---- 2. price expected to rise while stock is not plentiful
    if direction == "Rising" and days_left < cover:
        qty = shortfall
        why = f"Prices are forecast to rise {change:+.1f}% in 7 days and stock lasts only {days_left:.1f} days (target {cover})."
        if change is not None and change >= C.DECISION_STRONG_RISE_PCT:
            qty = shortfall * C.DECISION_STRONG_RISE_MULT
            why += " The rise is strong, so buy 20% extra."
        qty = round_qty(qty, unit)
        reasons += [why, f"Buy {fmt_qty(qty)} {unit} now, before it gets more expensive."]
        return _result("Buy Now", qty, 2, reasons, days_left, None, i, notes)

    # ---- 3. price expected to fall and stock is enough to wait
    if direction == "Falling" and days_left >= lead + C.DECISION_FALLING_EXTRA_DAYS:
        reasons += [f"Prices are forecast to fall {change:+.1f}% in 7 days.",
                    f"Stock lasts {days_left:.1f} days, more than the {lead}-day delivery time plus {C.DECISION_FALLING_EXTRA_DAYS} days, so you can wait for a lower price."]
        return _result("Wait", 0, 3, reasons, days_left, C.DECISION_CHECK_FALLING_DAYS, i, notes)

    # ---- 4. price is bad -> limited buy
    if bad_price:
        qty = round_qty(shortfall * C.DECISION_LIMITED_FRACTION, unit)
        reasons += [f"Stock lasts {days_left:.1f} days, but {note_price()}.",
                    f"Buy only {fmt_qty(qty)} {unit} (half of what is missing) and compare suppliers."]
        return _result("Buy Limited", qty, 2, reasons, days_left, None, i, notes)

    # ---- 5. enough stock
    if days_left >= cover:
        reasons += [f"Stock lasts {days_left:.1f} days, which covers your {cover}-day target. No need to buy now."]
        return _result("Wait", 0, 3, reasons, days_left, C.DECISION_CHECK_ENOUGH_DAYS, i, notes)

    # ---- 6. in between: top up carefully
    qty = round_qty(shortfall * C.DECISION_LIMITED_FRACTION, unit)
    reasons += [f"Stock lasts {days_left:.1f} days, below your {cover}-day target, and nothing special is happening with the price.",
                f"Top up with {fmt_qty(qty)} {unit} (half of what is missing)."]
    return _result("Buy Limited", qty, 2, reasons, days_left, None, i, notes)


def _result(action, qty, urgency, reasons, days_left, check_days, i, notes) -> dict:
    return {
        "action": action, "quantity": qty, "urgency": urgency, "reasons": reasons,
        "daysLeft": round(days_left, 1) if days_left is not None else None,
        "checkAgainInDays": check_days, "confidence": confidence_of(i.get("mape")),
        "dataQuality": "; ".join(notes) if notes else "Good",
    }


# ======================================================================== database wrapper
def _cheapest_supplier(db: Session, shop_id: int, product_id: int, today: dt.date) -> dict | None:
    """Supplier with the lowest average unit price over the last 90 days."""
    row = db.execute(
        select(Supplier.name, func.avg(Purchase.unit_price).label("avg_price"))
        .join(Supplier, Supplier.id == Purchase.supplier_id)
        .where(Purchase.shop_id == shop_id, Purchase.product_id == product_id,
               Purchase.purchase_date >= today - dt.timedelta(days=C.SUPPLIER_WINDOW_DAYS))
        .group_by(Supplier.name).order_by(func.avg(Purchase.unit_price)).limit(1)
    ).first()
    return {"name": row[0], "avgPrice": round(float(row[1]), 2)} if row else None


def _latest_purchase_has_anomaly(db: Session, shop_id: int, product_id: int) -> bool:
    last = db.execute(select(Purchase.id).where(Purchase.shop_id == shop_id, Purchase.product_id == product_id)
                      .order_by(Purchase.purchase_date.desc(), Purchase.id.desc()).limit(1)).scalar()
    if last is None:
        return False
    return db.execute(select(Alert.id).where(Alert.purchase_id == last, Alert.alert_type == "price_anomaly",
                                             Alert.is_read.is_(False))).first() is not None


def recommend_for_product(db: Session, shop: Shop, product: Product, sales_avg: dict | None = None,
                          today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    if sales_avg is None:
        sales_avg = {p["productId"]: p["avgDailySales"] for p in get_sales_summary(db, shop.id, C.SALES_WINDOW_DAYS)["products"]}

    fc = None
    if product.reference_commodity:
        try:
            fc = forecast_for_commodity(db, product.reference_commodity, 7)
        except NoModelError:
            fc = None
    fair = product_fair_price(db, shop, product)
    anomaly = _latest_purchase_has_anomaly(db, shop.id, product.id)

    d = decide({
        "stock": product.current_stock, "unit": product.unit, "avg_daily_sales": sales_avg.get(product.id),
        "reorder_level": product.reorder_level, "lead_time_days": shop.lead_time_days, "cover_days": shop.cover_days,
        "change_pct": fc["changePct"] if fc else None, "direction": fc["direction"] if fc else "Stable",
        "verdict": fair["verdict"], "variance_pct": fair["variancePct"], "anomaly": anomaly, "mape": fc["mape"] if fc else None,
    })
    if not product.reference_commodity:
        d["dataQuality"] = _join(d["dataQuality"], "No market data linked to this product")

    market_price = fc["latestPrice"] if fc else fair.get("referencePrice")
    return {
        "productId": product.id, "productName": product.name, "unit": product.unit, **d,
        "currentStock": product.current_stock,
        "currentMarketPrice": market_price,
        "forecastPrice7d": fc["forecast"][6]["price"] if fc else None,
        "changePct": fc["changePct"] if fc else None, "direction": fc["direction"] if fc else None,
        "fairPriceVerdict": fair["verdict"], "priceAnomaly": anomaly,
        "cheapestSupplier": _cheapest_supplier(db, shop.id, product.id, today),
    }


def _join(existing: str, note: str) -> str:
    return note if existing == "Good" else f"{existing}; {note}"


def recommend_all(db: Session, shop: Shop) -> list[dict]:
    """All products, most urgent first (then the fewest days of stock left)."""
    sales_avg = {p["productId"]: p["avgDailySales"] for p in get_sales_summary(db, shop.id, C.SALES_WINDOW_DAYS)["products"]}
    products = db.execute(select(Product).where(Product.shop_id == shop.id)).scalars().all()
    items = [recommend_for_product(db, shop, p, sales_avg) for p in products]
    items.sort(key=lambda r: (r["urgency"], r["daysLeft"] if r["daysLeft"] is not None else 1e9, r["productName"]))
    return items
