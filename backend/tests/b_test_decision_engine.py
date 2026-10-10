"""
Decision engine: table-driven cases for every rule + the database wrapper.
Defaults used below: lead time 3 days, cover 14 days, so for 10 units sold per day
need_lead = 30, target = 140.
"""
import datetime as dt

import pytest

from app.services.decision_engine import confidence_of, decide, round_qty
from conftest import TODAY

BASE = dict(stock=100.0, unit="kg", avg_daily_sales=10.0, reorder_level=50.0, lead_time_days=3, cover_days=14,
            change_pct=0.0, direction="Stable", verdict="Fair", variance_pct=0.0, anomaly=False, mape=1.5)


def case(**kw):
    return {**BASE, **kw}


# (name, inputs, expected action, expected quantity or None (= not checked), expected urgency, phrase in reasons)
CASES = [
    ("rule1 stockout -> Buy Now shortfall", case(stock=20), "Buy Now", 120.0, 1, "delivery time"),
    ("rule1 boundary: stock == need_lead", case(stock=30), "Buy Now", 110.0, 1, "at or below"),
    ("rule1 stockout but overpaying -> Buy Limited need_lead x1.2", case(stock=20, verdict="Overpaying", variance_pct=14.0), "Buy Limited", 36.0, 1, "compare suppliers"),
    ("rule1 stockout but anomaly -> Buy Limited", case(stock=20, anomaly=True), "Buy Limited", 36.0, 1, "abnormal"),
    ("rule2 rising -> Buy Now shortfall", case(stock=80, direction="Rising", change_pct=4.0), "Buy Now", 60.0, 2, "rise"),
    ("rule2 strong rise (>= 6 %) -> +20 %", case(stock=80, direction="Rising", change_pct=7.0), "Buy Now", 72.0, 2, "20% extra"),
    ("rule2 rising but plenty of stock falls through to Wait", case(stock=200, direction="Rising", change_pct=4.0), "Wait", 0, 3, "No need to buy"),
    ("rule3 falling + enough stock -> Wait 3 days", case(stock=80, direction="Falling", change_pct=-4.0), "Wait", 0, 3, "fall"),
    ("rule3 falling but stock only just above lead need -> not Wait", case(stock=40, direction="Falling", change_pct=-4.0), "Buy Limited", 50.0, 2, "Top up"),
    ("rule4 overpaying, stock ok -> Buy Limited 50 %", case(stock=100, verdict="Overpaying", variance_pct=12.0), "Buy Limited", 20.0, 2, "compare suppliers"),
    ("rule4 anomaly flag -> Buy Limited 50 %", case(stock=100, anomaly=True), "Buy Limited", 20.0, 2, "abnormal"),
    ("rule5 enough stock -> Wait 5 days", case(stock=150), "Wait", 0, 3, "covers your 14-day target"),
    ("rule5 boundary: days_left == cover_days", case(stock=140), "Wait", 0, 3, "No need"),
    ("rule6 in between -> Buy Limited 50 %", case(stock=100), "Buy Limited", 20.0, 2, "Top up"),
    ("packets are rounded UP to whole numbers", case(stock=33, unit="packet", avg_daily_sales=3.3, reorder_level=20, lead_time_days=3), "Buy Limited", None, 2, "Top up"),
]


@pytest.mark.parametrize("name, inputs, action, qty, urgency, phrase", CASES, ids=[c[0] for c in CASES])
def test_rules(name, inputs, action, qty, urgency, phrase):
    r = decide(inputs)
    assert r["action"] == action, r
    if qty is not None:
        assert r["quantity"] == pytest.approx(qty), r
    assert r["urgency"] == urgency
    assert any(phrase in line for line in r["reasons"]), r["reasons"]
    assert r["dataQuality"] == "Good"


def test_wait_check_again_days():
    assert decide(case(stock=80, direction="Falling", change_pct=-4.0))["checkAgainInDays"] == 3
    assert decide(case(stock=150))["checkAgainInDays"] == 5
    assert decide(case(stock=20))["checkAgainInDays"] is None


def test_packet_quantity_is_whole_number():
    r = decide(case(stock=33, unit="packet", avg_daily_sales=3.3, reorder_level=20))
    assert r["quantity"] == int(r["quantity"]) and r["quantity"] > 0


def test_kg_quantity_has_one_decimal():
    r = decide(case(stock=20.0, avg_daily_sales=3.37))
    assert round(r["quantity"], 1) == r["quantity"]


# ---------------------------------------------------------------- fallbacks
def test_no_sales_history_uses_reorder_level():
    r = decide(case(avg_daily_sales=None, stock=40, reorder_level=50))      # stock <= need_lead (= reorder)
    assert r["action"] == "Buy Now" and r["dataQuality"] == "No sales history - using reorder level"
    assert r["quantity"] == 110.0                                           # target 150 - stock 40
    assert r["daysLeft"] is not None


def test_no_sales_and_no_reorder_level_cannot_size_an_order():
    r = decide(case(avg_daily_sales=0, reorder_level=0))
    assert r["action"] == "Wait" and r["quantity"] == 0 and "cannot be worked out" in r["reasons"][0]


def test_missing_forecast_is_treated_as_stable_with_a_note():
    r = decide(case(change_pct=None, direction=None, stock=100))
    assert r["action"] == "Buy Limited"
    assert "No price forecast available" in r["dataQuality"]


def test_downgrade_on_overpaying_never_orders_more_than_needed():
    normal = decide(case(stock=20))
    cautious = decide(case(stock=20, verdict="Overpaying"))
    assert cautious["action"] == "Buy Limited" and cautious["quantity"] < normal["quantity"]


@pytest.mark.parametrize("mape, label", [(None, "Low"), (1.0, "High"), (2.99, "High"), (3.0, "Medium"), (5.9, "Medium"), (6.0, "Low"), (12, "Low")])
def test_confidence_levels(mape, label):
    assert confidence_of(mape) == label


@pytest.mark.parametrize("x, unit, expected", [(0, "kg", 0), (10.01, "kg", 10.1), (10.0, "kg", 10.0), (2.1, "packet", 3), (2.0, "box", 2)])
def test_round_qty(x, unit, expected):
    assert round_qty(x, unit) == expected


# ---------------------------------------------------------------- database wrapper + API
def _buy(client, d, qty, price, date):
    client.post("/api/purchases", headers=d["headers"], json={"productId": d["product"]["id"], "supplierId": d["supplier"]["id"],
                "quantity": qty, "unitPrice": price, "purchaseDate": date.isoformat()})


def _sell(client, d, qty, date):
    client.post("/api/sales", headers=d["headers"], json={"productId": d["product"]["id"], "quantity": qty, "saleDate": date.isoformat()})


def test_api_returns_full_recommendation(client, shop_with_data):
    d = shop_with_data
    _buy(client, d, 200, 40.0, TODAY - dt.timedelta(days=20))
    for i in range(10):
        _sell(client, d, 10, TODAY - dt.timedelta(days=i))                 # 10 per day for 10 days -> 100 left
    r = client.get("/api/recommendations/purchase", headers=d["headers"]).json()
    assert len(r) == 1
    rec = r[0]
    for key in ["productId", "productName", "unit", "action", "quantity", "urgency", "reasons", "currentStock", "daysLeft",
                "currentMarketPrice", "forecastPrice7d", "changePct", "direction", "fairPriceVerdict", "cheapestSupplier",
                "confidence", "checkAgainInDays", "dataQuality"]:
        assert key in rec, key
    assert rec["currentStock"] == 100 and rec["daysLeft"] == 10.0
    assert rec["action"] == "Buy Limited" and rec["quantity"] == 20.0         # rule 6: 10 days of stock, target 14 -> half of 40
    assert rec["cheapestSupplier"] == {"name": "ABC Traders", "avgPrice": 40.0}
    assert rec["fairPriceVerdict"] == "Fair"
    assert "No price forecast available" in rec["dataQuality"]                # no model trained in the test database
    assert client.get(f"/api/recommendations/purchase/{d['product']['id']}", headers=d["headers"]).json()["action"] == "Buy Limited"


def test_api_overpaying_downgrades_the_stockout_buy(client, shop_with_data):
    d = shop_with_data
    _buy(client, d, 40, 48.0, TODAY - dt.timedelta(days=5))                # 20 % above the Rs 40 market
    for i in range(4):
        _sell(client, d, 9, TODAY - dt.timedelta(days=i))                  # 4 left, selling 9 a day
    rec = client.get("/api/recommendations/purchase", headers=d["headers"]).json()[0]
    assert rec["fairPriceVerdict"] == "Overpaying" and rec["action"] == "Buy Limited" and rec["urgency"] == 1


def test_api_sorted_by_urgency(client, shop_with_data, create_product):
    d = shop_with_data
    create_product(d["headers"], "Sugar", openingStock=500, reorderLevel=10)
    _buy(client, d, 5, 40.0, TODAY - dt.timedelta(days=2))
    for i in range(2):
        _sell(client, d, 2, TODAY - dt.timedelta(days=i))
    names = [r["productName"] for r in client.get("/api/recommendations/purchase", headers=d["headers"]).json()]
    assert names[0] == "Rice"                                              # the one running out comes first


def test_api_private_to_shop(client, shop_with_data, register_user, create_shop):
    d = shop_with_data
    h2 = register_user("x@test.com")
    create_shop(h2)
    assert client.get("/api/recommendations/purchase", headers=h2).json() == []
    assert client.get(f"/api/recommendations/purchase/{d['product']['id']}", headers=h2).status_code == 404
    assert client.get("/api/recommendations/purchase").status_code == 401
