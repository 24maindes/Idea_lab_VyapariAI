"""Dashboard summary and price-trend API."""
import datetime as dt

from conftest import TODAY


def _buy(client, d, qty, price, days_ago):
    return client.post("/api/purchases", headers=d["headers"], json={"productId": d["product"]["id"], "supplierId": d["supplier"]["id"],
                       "quantity": qty, "unitPrice": price, "purchaseDate": (TODAY - dt.timedelta(days=days_ago)).isoformat()})


def test_summary_of_a_brand_new_shop_is_all_zeros(client, register_user, create_shop):
    h = register_user()
    create_shop(h)
    s = client.get("/api/dashboard/summary", headers=h).json()
    assert s["totalProducts"] == 0 and s["purchasesThisMonth"] == {"count": 0, "spend": 0.0}
    assert s["stock"] == {"units": 0.0, "value": 0.0} and s["unreadAlerts"] == 0 and s["lowStock"] == [] and s["topRecommendations"] == []
    assert s["onboarding"] == {"hasProducts": False, "hasSuppliers": False, "hasPurchases": False, "hasSales": False, "hasLinkedCommodities": False}


def test_summary_numbers(client, shop_with_data, create_product):
    d = shop_with_data
    create_product(d["headers"], "Sugar", openingStock=100, reorderLevel=10)
    _buy(client, d, 10, 40.0, 0)                                           # today: counts for this month
    client.post("/api/sales", headers=d["headers"], json={"productId": d["product"]["id"], "quantity": 4, "saleDate": TODAY.isoformat()})
    s = client.get("/api/dashboard/summary", headers=d["headers"]).json()
    assert s["totalProducts"] == 2
    assert s["purchasesThisMonth"] == {"count": 1, "spend": 400.0}
    assert s["stock"]["units"] == 106.0 and s["stock"]["value"] == 6 * 40.0          # Sugar has no purchase price -> value 0
    assert [p["name"] for p in s["lowStock"]] == ["Rice"]                          # Rice has 6 left, reorder level 10 -> low; Sugar (100) is fine


def test_low_stock_list_is_sorted_and_limited(client, register_user, create_shop, create_product):
    h = register_user()
    create_shop(h)
    for i in range(7):
        create_product(h, f"P{i}", openingStock=i, reorderLevel=10)
    low = client.get("/api/dashboard/summary", headers=h).json()["lowStock"]
    assert len(low) == 5 and [p["name"] for p in low] == ["P0", "P1", "P2", "P3", "P4"]


def test_onboarding_flags_follow_the_data(client, shop_with_data):
    d = shop_with_data
    o = client.get("/api/dashboard/summary", headers=d["headers"]).json()["onboarding"]
    assert o == {"hasProducts": True, "hasSuppliers": True, "hasPurchases": False, "hasSales": False, "hasLinkedCommodities": True}
    _buy(client, d, 10, 40.0, 1)
    client.post("/api/sales", headers=d["headers"], json={"productId": d["product"]["id"], "quantity": 1, "saleDate": TODAY.isoformat()})
    o = client.get("/api/dashboard/summary", headers=d["headers"]).json()["onboarding"]
    assert o["hasPurchases"] and o["hasSales"]


def test_recommendations_and_fair_price_parts(client, shop_with_data):
    d = shop_with_data
    for i in range(3):
        _buy(client, d, 10, 48.0, 20 - 5 * i)                              # 20 % above the Rs 40 market -> Overpaying
    s = client.get("/api/dashboard/summary", headers=d["headers"]).json()
    assert s["fairPrice"]["overpayingProducts"] == 1 and s["fairPrice"]["potentialSavings90d"] == 3 * 10 * 8
    assert len(s["topRecommendations"]) == 1 and s["topRecommendations"][0]["productName"] == "Rice" and s["topRecommendations"][0]["reason"]


def test_heavy_part_is_cached_then_cleared_by_writes(client, shop_with_data):
    d = shop_with_data
    first = client.get("/api/dashboard/summary", headers=d["headers"]).json()
    assert first["fairPrice"]["overpayingProducts"] == 0
    for i in range(3):
        _buy(client, d, 10, 48.0, 20 - 5 * i)                              # every write clears the shop's cache
    assert client.get("/api/dashboard/summary", headers=d["headers"]).json()["fairPrice"]["overpayingProducts"] == 1


def test_recent_activity_and_latest_alerts(client, shop_with_data):
    d = shop_with_data
    _buy(client, d, 10, 40.0, 1)
    client.post("/api/alerts/scan", headers=d["headers"])
    s = client.get("/api/dashboard/summary", headers=d["headers"]).json()
    assert s["recentActivity"][0]["text"].startswith("Purchase recorded") and len(s["recentActivity"]) <= 6
    assert s["unreadAlerts"] == len(client.get("/api/alerts?status=unread", headers=d["headers"]).json())


def test_price_trend(client, shop_with_data):
    d = shop_with_data
    _buy(client, d, 10, 41.0, 5)
    t = client.get(f"/api/dashboard/price-trend?productId={d['product']['id']}&days=60", headers=d["headers"]).json()
    assert t["commodity"] == "Rice" and len(t["history"]) >= 55 and t["forecast"] == []          # no trained model in the test database
    assert t["purchases"] == [{"date": (TODAY - dt.timedelta(days=5)).isoformat(), "price": 41.0, "supplier": "ABC Traders"}]
    assert client.get(f"/api/dashboard/price-trend?productId={d['product']['id']}&days=3", headers=d["headers"]).status_code == 422


def test_price_trend_without_commodity(client, register_user, create_shop, create_product):
    h = register_user()
    create_shop(h)
    p = create_product(h, "Soap")
    t = client.get(f"/api/dashboard/price-trend?productId={p['id']}", headers=h).json()
    assert t["commodity"] is None and t["history"] == [] and t["forecast"] == []


def test_dashboard_is_private(client, shop_with_data, register_user, create_shop):
    h2 = register_user("n@test.com")
    create_shop(h2)
    assert client.get("/api/dashboard/summary", headers=h2).json()["totalProducts"] == 0
    assert client.get(f"/api/dashboard/price-trend?productId={shop_with_data['product']['id']}", headers=h2).status_code == 404
    assert client.get("/api/dashboard/summary").status_code == 401
