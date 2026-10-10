"""A brand-new shop: 3 products, 2 purchases, no sales, no trained models. NOTHING may return a 500 error or crash."""
import datetime as dt

import pytest

from conftest import TODAY


@pytest.fixture()
def newbie(client, register_user, create_shop, create_product, create_supplier, add_reference):
    add_reference("Rice", 40.0, 120)
    add_reference("Sugar", 42.0, 120)
    h = register_user("new@test.com")
    create_shop(h)
    rice = create_product(h, "Rice", openingStock=10, reorderLevel=20, referenceCommodity="Rice", sellingPrice=48)
    sugar = create_product(h, "Sugar", openingStock=0, reorderLevel=10, referenceCommodity="Sugar")
    soap = create_product(h, "Soap", openingStock=5, reorderLevel=5)                      # not linked to any commodity
    s = create_supplier(h, "ABC", productIds=[rice["id"], sugar["id"]])
    for pid, price in ((rice["id"], 41.0), (sugar["id"], 43.0)):
        client.post("/api/purchases", headers=h, json={"productId": pid, "supplierId": s["id"], "quantity": 10, "unitPrice": price,
                    "purchaseDate": (TODAY - dt.timedelta(days=3)).isoformat()})
    return {"headers": h, "rice": rice, "sugar": sugar, "soap": soap, "supplier": s}


def ok(client, d, path):
    r = client.get(path, headers=d["headers"])
    assert r.status_code == 200, (path, r.status_code, r.text[:300])
    return r.json()


def test_no_endpoint_crashes_for_a_new_shop(client, newbie):
    d = newbie
    paths = ["/api/dashboard/summary", "/api/inventory", "/api/products", "/api/suppliers", "/api/purchases", "/api/sales", "/api/sales/summary",
             "/api/activity", "/api/alerts", "/api/alerts/count", "/api/recommendations/purchase", "/api/recommendations/selling-price",
             "/api/analysis/fair-price", "/api/forecast/models", "/api/advisor/history", "/api/reference/commodities"]
    paths += [f"/api/{x}/{p['id']}" for x in ("forecast", "analysis/fair-price", "recommendations/purchase", "recommendations/selling-price")
              for p in (d["rice"], d["sugar"], d["soap"])]
    paths += [f"/api/dashboard/price-trend?productId={p['id']}" for p in (d["rice"], d["sugar"], d["soap"])]
    paths += [f"/api/suppliers/comparison?productId={p['id']}" for p in (d["rice"], d["soap"])]
    for path in paths:
        ok(client, d, path)
    assert client.post("/api/alerts/scan", headers=d["headers"]).status_code == 200
    assert client.post("/api/forecast/retrain?commodity=Rice", headers=d["headers"]).status_code in (202, 409)


def test_fair_price_works_from_reference_data(client, newbie):
    f = ok(client, newbie, f"/api/analysis/fair-price/{newbie['rice']['id']}")
    assert f["hasMarketData"] and f["referencePrice"] == 40.0 and f["variancePct"] == 2.5 and f["verdict"] == "Fair"
    soap = ok(client, newbie, f"/api/analysis/fair-price/{newbie['soap']['id']}")
    assert soap["hasMarketData"] is False and soap["verdict"] is None and soap["lastPurchasePrice"] is None


def test_forecast_says_why_it_is_missing(client, newbie):
    r = ok(client, newbie, f"/api/forecast/{newbie['rice']['id']}")
    assert r["available"] is False and "Retrain" in r["reason"]
    assert "not linked" in ok(client, newbie, f"/api/forecast/{newbie['soap']['id']}")["reason"]


def test_decision_engine_falls_back_to_reorder_level_with_a_note(client, newbie):
    recs = {r["productName"]: r for r in ok(client, newbie, "/api/recommendations/purchase")}
    rice = recs["Rice"]                                         # stock 20 (10 + 10 bought), reorder level 20, no sales
    assert "No sales history - using reorder level" in rice["dataQuality"] and "No price forecast available" in rice["dataQuality"]
    assert rice["action"] == "Buy Now" and rice["quantity"] > 0 and rice["daysLeft"] is not None
    assert recs["Sugar"]["action"] in ("Buy Now", "Buy Limited", "Wait")
    soap = recs["Soap"]
    assert "No market data linked" in soap["dataQuality"] and soap["cheapestSupplier"] is None and soap["fairPriceVerdict"] is None


def test_decision_with_no_sales_and_no_reorder_level_never_orders_nothing_silently(client, register_user, create_shop, create_product):
    h = register_user("zero@test.com")
    create_shop(h)
    create_product(h, "Thing", openingStock=3, reorderLevel=0)
    r = client.get("/api/recommendations/purchase", headers=h).json()[0]
    assert r["action"] == "Wait" and "cannot be worked out" in r["reasons"][0] and "No sales history and no reorder level" in r["dataQuality"]


def test_pricing_engine_falls_back_to_target_margin_or_market(client, newbie):
    rows = {r["productName"]: r for r in ok(client, newbie, "/api/recommendations/selling-price")}
    assert rows["Rice"]["recommended"] is not None and rows["Rice"]["costBasis"] == 41.0
    soap = rows["Soap"]
    assert soap["recommended"] is None and soap["marketPrice"] is None and len(soap["warnings"]) == 2          # no cost and no market
    assert any("No purchases" in w for w in soap["warnings"]) and any("No market price" in w for w in soap["warnings"])


def test_dashboard_for_a_shop_without_sales(client, newbie):
    s = ok(client, newbie, "/api/dashboard/summary")
    assert s["onboarding"]["hasPurchases"] and not s["onboarding"]["hasSales"]
    assert s["totalProducts"] == 3 and len(s["topRecommendations"]) == 3 and s["fairPrice"]["overpayingProducts"] == 0
    assert s["stock"]["value"] > 0


def test_inventory_has_null_cover_not_zero_or_crash(client, newbie):
    rows = {r["name"]: r for r in ok(client, newbie, "/api/inventory")}
    assert rows["Rice"]["avgDailySales"] is None and rows["Rice"]["daysOfCover"] is None and rows["Soap"]["lastPurchaseDate"] is None


def test_advisor_answers_even_with_almost_no_data(client, newbie):
    a = client.post("/api/advisor/chat", headers=newbie["headers"], json={"message": "Should I buy rice?", "language": "en"}).json()
    assert a["usedFallback"] is True and "Rice" in a["answer"] and a["sources"]
    assert client.post("/api/advisor/chat", headers=newbie["headers"], json={"message": "price of soap", "language": "en"}).status_code == 200


def test_context_missing_list(client, newbie, db):
    from app.models import Product, Shop
    from app.services.advisor import retrieval
    shop = db.query(Shop).first()
    soap = db.query(Product).filter_by(name="Soap").one()
    rice = db.query(Product).filter_by(name="Rice").one()
    ctx = retrieval.build_context(db, shop, [soap, rice], {"general"})
    missing = " | ".join(ctx["missing"])
    assert "Soap is not linked to a market commodity" in missing and "No purchases recorded for Soap" in missing
    assert "No trained forecast model for Rice" in missing


def test_alerts_scan_on_low_data(client, newbie):
    client.post("/api/alerts/scan", headers=newbie["headers"])
    types = {a["type"] for a in ok(client, newbie, "/api/alerts")}
    assert "low_stock" in types and "price_anomaly" not in types


def test_supplier_comparison_with_two_purchases_says_not_enough_data(client, newbie):
    r = ok(client, newbie, f"/api/suppliers/comparison?productId={newbie['rice']['id']}")
    assert r["suppliers"][0]["stability"] == "Not enough data" and r["suppliers"][0]["bestValue"] is False


def test_totally_empty_shop_everything_is_empty_not_error(client, register_user, create_shop):
    h = register_user("empty@test.com")
    create_shop(h)
    for path in ["/api/dashboard/summary", "/api/inventory", "/api/recommendations/purchase", "/api/recommendations/selling-price",
                 "/api/analysis/fair-price", "/api/sales/summary", "/api/purchases", "/api/alerts"]:
        assert client.get(path, headers=h).status_code == 200, path
    assert client.post("/api/advisor/chat", headers=h, json={"message": "What should I buy today?", "language": "en"}).status_code == 200
    assert client.post("/api/alerts/scan", headers=h).json()["newAlerts"] == 0


def test_user_without_a_shop_gets_a_clear_404_not_a_500(client, register_user):
    h = register_user("noshop@test.com")
    for path in ["/api/dashboard/summary", "/api/products", "/api/inventory", "/api/recommendations/purchase", "/api/advisor/history"]:
        r = client.get(path, headers=h)
        assert r.status_code == 404 and r.json()["detail"] == "Shop not set up yet", path
