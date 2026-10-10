"""Supplier statistics, comparison API, shop parameter validation and password change."""
import datetime as dt

import pytest

from app.services.supplier_stats import stability_of
from conftest import TODAY


@pytest.mark.parametrize("count, cv, expected", [
    (2, 1.0, "Not enough data"), (3, None, "Not enough data"),
    (3, 0.0, "Stable"), (3, 2.99, "Stable"), (3, 3.0, "Moderate"), (3, 7.0, "Moderate"), (3, 7.01, "Volatile"), (10, 15, "Volatile"),
])
def test_stability_thresholds(count, cv, expected):
    assert stability_of(count, cv) == expected


def _supplier(client, d, name):
    r = client.post("/api/suppliers", headers=d["headers"], json={"name": name, "productIds": [d["product"]["id"]]})
    return r.json()["id"]


def _buy(client, d, sid, price, days_ago, qty=5):
    r = client.post("/api/purchases", headers=d["headers"], json={"productId": d["product"]["id"], "supplierId": sid, "quantity": qty,
                    "unitPrice": price, "purchaseDate": (TODAY - dt.timedelta(days=days_ago)).isoformat()})
    assert r.status_code == 201, r.text


def _setup(client, d):
    cheap_stable = d["supplier"]["id"]                              # ABC Traders: ~Rs 39, tiny noise
    volatile = _supplier(client, d, "XYZ Wholesale")                # cheaper on average but jumps +/-12 %
    young = _supplier(client, d, "New Supplier")                    # only 2 purchases
    for i, p in enumerate([39.0, 39.2, 38.9, 39.1, 39.0]):
        _buy(client, d, cheap_stable, p, 50 - 7 * i)
    for i, p in enumerate([34.0, 45.0, 33.0, 46.0, 35.0]):
        _buy(client, d, volatile, p, 49 - 7 * i)
    for i, p in enumerate([30.0, 30.0]):
        _buy(client, d, young, p, 20 - 5 * i)
    return cheap_stable, volatile, young


def test_comparison_stability_and_best_value(client, shop_with_data):
    d = shop_with_data
    _setup(client, d)
    r = client.get(f"/api/suppliers/comparison?productId={d['product']['id']}", headers=d["headers"]).json()
    by = {s["supplierName"]: s for s in r["suppliers"]}
    assert r["productName"] == "Rice" and r["marketAvgPrice"] == 40.0
    assert by["ABC Traders"]["stability"] == "Stable"
    assert by["XYZ Wholesale"]["stability"] == "Volatile"
    assert by["New Supplier"]["stability"] == "Not enough data"
    # the cheapest supplier overall (New Supplier, Rs 30) is NOT best value (too little data); the volatile one is excluded too
    assert [s["supplierName"] for s in r["suppliers"] if s["bestValue"]] == ["ABC Traders"]
    assert [s["avgPrice"] for s in r["suppliers"]] == sorted(s["avgPrice"] for s in r["suppliers"])     # sorted by price
    assert by["ABC Traders"]["avgVarianceVsMarketPct"] == pytest.approx(-2.4, abs=0.2)
    assert by["ABC Traders"]["minPrice"] == 38.9 and by["ABC Traders"]["maxPrice"] == 39.2


def test_stats_numbers_are_exact(client, shop_with_data, db):
    from app.services.supplier_stats import supplier_stats
    d = shop_with_data
    sid = d["supplier"]["id"]
    for i, p in enumerate([40.0, 42.0, 44.0]):
        _buy(client, d, sid, p, 30 - 10 * i)
    shop_id = d["shop"]["id"]
    row = supplier_stats(db, shop_id)[0]
    assert row["purchaseCount"] == 3 and row["avgPrice"] == 42.0 and row["minPrice"] == 40.0 and row["maxPrice"] == 44.0
    assert row["latestPrice"] == 44.0 and row["stdDev"] == pytest.approx(1.63, abs=0.01)
    assert row["coefficientOfVariationPct"] == pytest.approx(3.9, abs=0.1) and row["stability"] == "Moderate"
    assert row["bestValue"] is True                                  # the only eligible supplier


def test_old_purchases_outside_window_are_ignored(client, shop_with_data):
    d = shop_with_data
    _buy(client, d, d["supplier"]["id"], 40.0, 400)
    r = client.get(f"/api/suppliers/comparison?productId={d['product']['id']}&days=180", headers=d["headers"]).json()
    assert r["suppliers"] == []


def test_supplier_price_history_endpoint(client, shop_with_data):
    d = shop_with_data
    sid = d["supplier"]["id"]
    _buy(client, d, sid, 41.0, 10)
    _buy(client, d, sid, 43.0, 3)
    r = client.get(f"/api/suppliers/{sid}/prices?productId={d['product']['id']}", headers=d["headers"]).json()
    assert [p["price"] for p in r["prices"]] == [41.0, 43.0] and len(r["reference"]) > 50 and r["supplierName"] == "ABC Traders"


def test_comparison_routes_are_not_swallowed_by_id_routes(client, shop_with_data):
    r = client.get(f"/api/suppliers/comparison?productId={shop_with_data['product']['id']}", headers=shop_with_data["headers"])
    assert r.status_code == 200


def test_comparison_private_to_shop(client, shop_with_data, register_user, create_shop):
    d = shop_with_data
    h2 = register_user("o2@test.com")
    create_shop(h2)
    assert client.get(f"/api/suppliers/comparison?productId={d['product']['id']}", headers=h2).status_code == 404
    assert client.get(f"/api/suppliers/{d['supplier']['id']}/prices?productId={d['product']['id']}", headers=h2).status_code == 404


# ---------------------------------------------------------------- shop parameter validation (PUT /api/shop)
@pytest.mark.parametrize("body", [
    {"targetMarginPct": -1}, {"targetMarginPct": 101}, {"minMarginPct": 101},
    {"leadTimeDays": -1}, {"leadTimeDays": 31}, {"coverDays": 0}, {"coverDays": 91},
    {"anomalyThresholdPct": 4.9}, {"anomalyThresholdPct": 50.1}, {"zCutoff": 1.4}, {"zCutoff": 4.1}, {"language": "fr"},
])
def test_shop_parameter_ranges_rejected(client, register_user, create_shop, body):
    h = register_user()
    create_shop(h)
    assert client.put("/api/shop", headers=h, json=body).status_code == 422


@pytest.mark.parametrize("body", [
    {"targetMarginPct": 0, "minMarginPct": 0}, {"targetMarginPct": 100, "minMarginPct": 100}, {"leadTimeDays": 0}, {"leadTimeDays": 30},
    {"coverDays": 1}, {"coverDays": 90}, {"anomalyThresholdPct": 5}, {"anomalyThresholdPct": 50}, {"zCutoff": 1.5}, {"zCutoff": 4}, {"language": "hi"}, {"language": "mr"},
])
def test_shop_parameter_boundaries_accepted(client, register_user, create_shop, body):
    h = register_user()
    create_shop(h)
    assert client.put("/api/shop", headers=h, json=body).status_code == 200


def test_min_margin_cannot_exceed_target_margin(client, register_user, create_shop):
    h = register_user()
    create_shop(h)
    r = client.put("/api/shop", headers=h, json={"minMarginPct": 30})            # target is 15
    assert r.status_code == 422 and "cannot be higher" in str(r.json()["detail"])
    assert client.put("/api/shop", headers=h, json={"minMarginPct": 30, "targetMarginPct": 40}).status_code == 200


def test_values_persist(client, register_user, create_shop):
    h = register_user()
    create_shop(h)
    client.put("/api/shop", headers=h, json={"coverDays": 21, "zCutoff": 3, "language": "mr"})
    s = client.get("/api/shop", headers=h).json()
    assert s["coverDays"] == 21 and s["zCutoff"] == 3 and s["language"] == "mr"


# ---------------------------------------------------------------- password
def test_change_password_flow(client, register_user):
    h = register_user("pw@test.com", password="oldpass1")
    assert client.put("/api/auth/password", headers=h, json={"oldPassword": "WRONG", "newPassword": "newpass1"}).status_code == 400
    assert client.put("/api/auth/password", headers=h, json={"oldPassword": "oldpass1", "newPassword": "123"}).status_code == 422
    assert client.put("/api/auth/password", headers=h, json={"oldPassword": "oldpass1", "newPassword": "oldpass1"}).status_code == 400
    assert client.put("/api/auth/password", headers=h, json={"oldPassword": "oldpass1", "newPassword": "newpass1"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "pw@test.com", "password": "oldpass1"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "pw@test.com", "password": "newpass1"}).status_code == 200


def test_change_password_needs_login(client):
    assert client.put("/api/auth/password", json={"oldPassword": "a", "newPassword": "123456"}).status_code == 401
