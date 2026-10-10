"""
advisor/retrieval.py - the "R" in RAG: collect the REAL numbers the answer must be based on.

Retrieval is STRUCTURED: we call the same services the pages use (fair price, forecast, decision engine, selling price,
supplier statistics, sales summary, alerts). No vector search, because the data is numbers in tables, not free text.

build_context(db, shop, products, topics) -> a compact dict that is later pasted into the prompt.
It stays under about 3000 tokens (about 12,000 characters): when it is too long the longest lists are shortened first.
"""
import datetime as dt
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Product, Purchase, Shop, Supplier
from app.services.decision_engine import recommend_all, recommend_for_product
from app.services.fair_price import product_fair_price
from app.services.forecast_service import NoModelError, forecast_for_commodity
from app.services.pricing_engine import recommend_selling_price
from app.services.sales_summary import get_sales_summary
from app.services.supplier_stats import supplier_stats

MAX_CHARS = 12000          # about 3000 tokens


def _rs(x, unit=None) -> str | None:
    if x is None:
        return None
    return f"Rs {x:g}" + (f"/{unit}" if unit else "")


def _last_purchases(db: Session, shop_id: int, product_id: int, n: int = 10) -> list[dict]:
    rows = db.execute(select(Purchase.purchase_date, Supplier.name, Purchase.quantity, Purchase.unit_price)
                      .outerjoin(Supplier, Supplier.id == Purchase.supplier_id)
                      .where(Purchase.shop_id == shop_id, Purchase.product_id == product_id)
                      .order_by(Purchase.purchase_date.desc(), Purchase.id.desc()).limit(n)).all()
    return [{"date": d.isoformat(), "supplier": s or "Unknown", "quantity": q, "unitPrice": p} for d, s, q, p in rows]


def product_context(db: Session, shop: Shop, product: Product, topics: set[str], sales_avg: dict) -> dict:
    """Everything known about ONE product (all sections; trimming happens later)."""
    fair = product_fair_price(db, shop, product)
    rec = recommend_for_product(db, shop, product, sales_avg)
    sell = recommend_selling_price(db, shop, product)
    forecast, missing = None, []
    if product.reference_commodity:
        try:
            f = forecast_for_commodity(db, product.reference_commodity, 7)
            forecast = {"priceNow": f["latestPrice"], "priceIn7Days": f["forecast"][6]["price"], "changePct": f["changePct"],
                        "direction": f["direction"], "modelMape": f["mape"], "modelName": f["modelName"]}
        except NoModelError:
            missing.append(f"No trained forecast model for {product.name}")
    else:
        missing.append(f"{product.name} is not linked to a market commodity, so there is no market price or forecast")
    if fair["lastPurchasePrice"] is None:
        missing.append(f"No purchases recorded for {product.name}")
    if fair["hasMarketData"] and fair["referencePrice"] is None and fair["lastPurchasePrice"] is not None:
        missing.append(f"No market price found for the date of the last {product.name} purchase")

    suppliers = [{"supplier": s["supplierName"], "avgPrice": s["avgPrice"], "stability": s["stability"],
                  "avgVsMarketPct": s["avgVarianceVsMarketPct"], "purchases": s["purchaseCount"], "bestValue": s["bestValue"]}
                 for s in supplier_stats(db, shop.id, product.id, 180)]
    unread = db.execute(select(Alert.message).where(Alert.shop_id == shop.id, Alert.product_id == product.id,
                                                    Alert.is_read.is_(False)).order_by(Alert.created_at.desc()).limit(3)).scalars().all()
    avg = sales_avg.get(product.id)
    return {
        "name": product.name, "unit": product.unit, "category": product.category,
        "stock": product.current_stock, "reorderLevel": product.reorder_level,
        "avgDailySales": avg, "daysOfStockLeft": rec["daysLeft"],
        "lastPurchases": _last_purchases(db, shop.id, product.id, 10),
        "fairPrice": {"lastPurchasePrice": fair["lastPurchasePrice"], "lastPurchaseDate": fair["lastPurchaseDate"].isoformat() if fair["lastPurchaseDate"] else None,
                      "marketPrice": fair["referencePrice"], "variancePct": fair["variancePct"], "verdict": fair["verdict"],
                      "potentialSavings180d": fair["potentialSavings"]},
        "forecast": forecast,
        "purchaseRecommendation": {"action": rec["action"], "quantity": rec["quantity"], "checkAgainInDays": rec["checkAgainInDays"],
                                   "reasons": rec["reasons"], "confidence": rec["confidence"]},
        "sellingPrice": {"recommended": sell["recommended"], "rangeLow": sell["rangeLow"], "rangeHigh": sell["rangeHigh"],
                         "expectedMarginPct": sell["expectedMarginPct"], "currentPrice": sell["currentPrice"], "warnings": sell["warnings"]},
        "suppliers": suppliers, "unreadAlerts": list(unread), "_missing": missing,
    }


def overview_context(db: Session, shop: Shop) -> dict:
    recs = recommend_all(db, shop)
    products = db.execute(select(Product).where(Product.shop_id == shop.id)).scalars().all()
    low = [{"name": p.name, "stock": p.current_stock, "unit": p.unit, "reorderLevel": p.reorder_level}
           for p in products if p.current_stock <= p.reorder_level][:5]
    unread = db.execute(select(Alert.message).where(Alert.shop_id == shop.id, Alert.is_read.is_(False))
                        .order_by(Alert.created_at.desc()).limit(3)).scalars().all()
    return {
        "topRecommendations": [{"product": r["productName"], "action": r["action"], "quantity": r["quantity"], "unit": r["unit"],
                                "reason": r["reasons"][0] if r["reasons"] else ""} for r in recs[:3]],
        "lowStock": low, "unreadAlerts": list(unread),
        "overpayingProducts": [r["productName"] for r in recs if r["fairPriceVerdict"] == "Overpaying"],
    }


def _data_date(db: Session, shop_id: int) -> str | None:
    last = db.execute(select(Purchase.purchase_date).where(Purchase.shop_id == shop_id).order_by(Purchase.purchase_date.desc()).limit(1)).scalar()
    return last.isoformat() if last else None


def _size(ctx: dict) -> int:
    return len(json.dumps(ctx, ensure_ascii=False, default=str))


def _trim(ctx: dict) -> dict:
    """Shorten the longest lists first until the context fits the budget."""
    for keep in (10, 6, 4, 3, 2):
        if _size(ctx) <= MAX_CHARS:
            return ctx
        for p in ctx.get("products", []):
            p["lastPurchases"] = p["lastPurchases"][:keep]
            p["suppliers"] = p["suppliers"][:max(keep - 1, 2)]
    for p in ctx.get("products", []):                     # still too big: drop the least useful parts
        p["suppliers"] = p["suppliers"][:2]
        p["purchaseRecommendation"]["reasons"] = p["purchaseRecommendation"]["reasons"][:1]
        p["lastPurchases"] = p["lastPurchases"][:2]
    return ctx


def build_context(db: Session, shop: Shop, products: list[Product], topics: set[str], lean: bool = False, notes: list[str] | None = None) -> dict:
    sales_avg = {p["productId"]: p["avgDailySales"] for p in get_sales_summary(db, shop.id, 30)["products"]}
    ctx: dict = {"shop": {"name": shop.shop_name, "city": shop.location, "leadTimeDays": shop.lead_time_days, "coverDays": shop.cover_days,
                          "targetMarginPct": shop.target_margin_pct},
                 "today": dt.date.today().isoformat(), "dataDate": _data_date(db, shop.id), "topics": sorted(topics), "missing": [],
                 "notes": list(notes or [])}
    if products:
        ctx["products"] = [product_context(db, shop, p, topics, sales_avg) for p in products[:(2 if lean else 3)]]     # at most 3 products per answer
        if lean:                                              # slow responses: send less (old purchases are dropped first)
            for p in ctx["products"]:
                p["lastPurchases"] = p["lastPurchases"][:3]
                p["suppliers"] = p["suppliers"][:2]
                p["purchaseRecommendation"]["reasons"] = p["purchaseRecommendation"]["reasons"][:1]
        for p in ctx["products"]:
            ctx["missing"] += p.pop("_missing")
    else:
        ctx["overview"] = overview_context(db, shop)
    return _trim(ctx)


# ---------------------------------------------------------------- human-readable "sources used"
def sources_from_context(ctx: dict, topics: set[str]) -> list[dict]:
    """Facts that were really available to the answer, as {label, value}. Shown under the answer in the UI."""
    out: list[dict] = []
    for p in ctx.get("products", []):
        prefix = f"{p['name']}: " if len(ctx["products"]) > 1 else ""
        u = p["unit"]
        fp, fc, rec, sp = p["fairPrice"], p["forecast"], p["purchaseRecommendation"], p["sellingPrice"]
        if fp["lastPurchasePrice"] is not None:
            out.append({"label": prefix + "Last purchase price", "value": f"{_rs(fp['lastPurchasePrice'], u)} on {fp['lastPurchaseDate']}"})
        if fp["marketPrice"] is not None:
            out.append({"label": prefix + "Market price on that day", "value": _rs(fp["marketPrice"], u)})
        if fp["variancePct"] is not None:
            out.append({"label": prefix + "Difference from market", "value": f"{fp['variancePct']:+.1f}% ({fp['verdict']})"})
        out.append({"label": prefix + "Stock now", "value": f"{p['stock']:g} {u}" + (f" (about {p['daysOfStockLeft']:g} days)" if p["daysOfStockLeft"] is not None else "")})
        if p["avgDailySales"]:
            out.append({"label": prefix + "Average daily sales", "value": f"{p['avgDailySales']:g} {u}"})
        if fc:
            out.append({"label": prefix + "Price forecast (7 days)", "value": f"{_rs(fc['priceNow'])} to {_rs(fc['priceIn7Days'])} ({fc['changePct']:+.1f}%, {fc['direction']})"})
        out.append({"label": prefix + "Purchase advice", "value": rec["action"] + (f" {rec['quantity']:g} {u}" if rec["quantity"] else "")})
        if sp["recommended"] is not None and ("selling_price" in topics or "general" in topics):
            out.append({"label": prefix + "Recommended selling price", "value": f"{_rs(sp['recommended'], u)} (range {_rs(sp['rangeLow'])} - {_rs(sp['rangeHigh'])})"})
        best = next((s for s in p["suppliers"] if s["bestValue"]), None) or (p["suppliers"][0] if p["suppliers"] else None)
        if best and ("supplier" in topics or "buy_decision" in topics):
            out.append({"label": prefix + "Best supplier", "value": f"{best['supplier']} (average {_rs(best['avgPrice'], u)})"})
    ov = ctx.get("overview")
    if ov:
        for r in ov["topRecommendations"]:
            out.append({"label": f"Advice for {r['product']}", "value": r["action"] + (f" {r['quantity']:g} {r['unit']}" if r["quantity"] else "")})
        if ov["lowStock"]:
            out.append({"label": "Low stock", "value": ", ".join(x["name"] for x in ov["lowStock"])})
        if ov["overpayingProducts"]:
            out.append({"label": "Overpaying on", "value": ", ".join(ov["overpayingProducts"])})
        out.append({"label": "Unread alerts", "value": str(len(ov["unreadAlerts"]))})
    return out
