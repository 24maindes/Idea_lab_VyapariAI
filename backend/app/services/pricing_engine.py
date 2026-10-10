"""
services/pricing_engine.py - what should I SELL this product at?

Idea in plain words:
  cost      = what the last 5 purchases cost on average (weighted by quantity)
  floor     = cost + the minimum margin the shopkeeper accepts   (never sell below this)
  target    = cost + the margin the shopkeeper WANTS
  market    = what other shops charge today (retail reference price)
  recommended = the market price, but kept between floor and target
                (follow the market, yet never lose money and never be greedy)
  range     = from 3 % below to 5 % above the recommended price
"""
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, Purchase, ReferencePrice, Shop
from app.services import config as C
from app.services.sales_summary import weighted_avg_cost


def round_price(x: float | None, unit: str | None) -> float | None:
    """Shop prices are quoted in tidy steps: Rs 0.5 for kg/litre, whole rupees for packets/boxes."""
    if x is None:
        return None
    step = 1.0 if unit in ("packet", "box") else 0.5
    return round(round(x / step) * step, 2)


def compute_pricing(*, cost, min_margin_pct, margin_pct, market, unit, current_price) -> dict:
    """Pure function: numbers in, price recommendation out."""
    warnings: list[str] = []
    floor = cost * (1 + min_margin_pct / 100) if cost is not None else None
    target = cost * (1 + margin_pct / 100) if cost is not None else None

    if cost is None:
        warnings.append("No purchases yet, so your cost is unknown. Record a purchase to get a cost-based price.")
    if market is None:
        warnings.append("No market price available for this product.")

    if cost is None and market is None:
        recommended = None
    elif cost is None:
        recommended = market                                       # no cost: follow the market
    elif market is None:
        recommended = target                                       # no market: use the margin target
    else:
        recommended = min(max(market, floor), max(target, floor))  # clamp the market between floor and target
        if market < floor:
            warnings.append("Market price is below your cost floor - consider skipping this restock")

    low = high = None
    if recommended is not None:
        low = recommended * C.PRICE_RANGE_LOW_FACTOR
        if floor is not None:
            low = max(floor, low)
        high = recommended * C.PRICE_RANGE_HIGH_FACTOR

    rec_r = round_price(recommended, unit)
    margin = round((rec_r / cost - 1) * 100, 1) if (rec_r is not None and cost) else None
    gap = round((current_price / rec_r - 1) * 100, 1) if (current_price and rec_r) else None

    if current_price and market:
        diff = (current_price / market - 1) * 100
        if diff < -C.PRICE_VS_MARKET_WARN_PCT:
            warnings.append(f"Your current price is {abs(diff):.0f}% below the market - you may be giving away margin")
        elif diff > C.PRICE_VS_MARKET_WARN_PCT:
            warnings.append(f"Your current price is {diff:.0f}% above the market - customers may go elsewhere")
    if current_price and floor and current_price < floor:
        warnings.append("Your current price is below your cost floor")

    return {
        "costBasis": round(cost, 2) if cost is not None else None,
        "floorPrice": round_price(floor, unit), "targetPrice": round_price(target, unit),
        "marketPrice": round(market, 2) if market is not None else None,
        "recommended": rec_r, "rangeLow": round_price(low, unit), "rangeHigh": round_price(high, unit),
        "expectedMarginPct": margin, "currentPrice": current_price, "gapToRecommendedPct": gap, "warnings": warnings,
    }


def latest_market_price(db: Session, commodity: str | None, today: dt.date | None = None) -> float | None:
    """Latest RETAIL reference price (or wholesale x 1.12 when retail is missing). None if no reference at all."""
    if not commodity:
        return None
    row = db.execute(select(ReferencePrice.retail_price, ReferencePrice.wholesale_price)
                     .where(ReferencePrice.commodity == commodity, *([ReferencePrice.price_date <= today] if today else []))
                     .order_by(ReferencePrice.price_date.desc()).limit(1)).first()
    if row is None:
        return None
    retail, wholesale = row
    if retail:
        return float(retail)
    return float(wholesale) * C.RETAIL_FROM_WHOLESALE if wholesale else None


def _cost_basis(db: Session, shop_id: int, product_id: int) -> float | None:
    """Weighted average of the last 5 purchases; falls back to the latest purchase price."""
    avg = weighted_avg_cost(db, shop_id, [product_id], C.COST_BASIS_PURCHASES).get(product_id)
    if avg is not None:
        return avg
    last = db.execute(select(Purchase.unit_price).where(Purchase.shop_id == shop_id, Purchase.product_id == product_id)
                      .order_by(Purchase.purchase_date.desc(), Purchase.id.desc()).limit(1)).scalar()
    return float(last) if last is not None else None


def recommend_selling_price(db: Session, shop: Shop, product: Product, target_margin_pct: float | None = None) -> dict:
    margin = target_margin_pct if target_margin_pct is not None else shop.target_margin_pct
    result = compute_pricing(
        cost=_cost_basis(db, shop.id, product.id), min_margin_pct=shop.min_margin_pct, margin_pct=margin,
        market=latest_market_price(db, product.reference_commodity), unit=product.unit, current_price=product.selling_price)
    return {"productId": product.id, "productName": product.name, "unit": product.unit, "targetMarginPct": margin, **result}


def recommend_selling_prices(db: Session, shop: Shop, target_margin_pct: float | None = None) -> list[dict]:
    products = db.execute(select(Product).where(Product.shop_id == shop.id).order_by(Product.name)).scalars().all()
    return [recommend_selling_price(db, shop, p, target_margin_pct) for p in products]
