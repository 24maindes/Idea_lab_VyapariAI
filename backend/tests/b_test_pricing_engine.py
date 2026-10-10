"""Selling-price engine: pure maths + API."""
import datetime as dt

import pytest

from app.services.pricing_engine import compute_pricing, round_price
from conftest import TODAY


def price(**kw):
    base = dict(cost=100.0, min_margin_pct=5, margin_pct=15, market=112.0, unit="kg", current_price=None)
    return compute_pricing(**{**base, **kw})


def test_floor_and_target_values():
    r = price()
    assert r["floorPrice"] == 105.0 and r["targetPrice"] == 115.0


def test_market_inside_band_is_followed():
    r = price(market=110.0)
    assert r["recommended"] == 110.0 and r["expectedMarginPct"] == 10.0 and r["warnings"] == []


def test_floor_is_respected_when_market_is_too_low():
    r = price(market=95.0)
    assert r["recommended"] == 105.0 and r["rangeLow"] >= r["floorPrice"]
    assert any("below your cost floor" in w and "skipping this restock" in w for w in r["warnings"])


def test_market_above_target_is_clamped_to_target():
    r = price(market=140.0)
    assert r["recommended"] == 115.0


def test_range_is_97_to_105_percent_but_never_below_floor():
    r = price(market=112.0)
    assert r["rangeLow"] == round_price(112 * 0.97, "kg") and r["rangeHigh"] == round_price(112 * 1.05, "kg")
    low_market = price(market=106.0)                                  # 106 x 0.97 = 102.8 < floor 105
    assert low_market["rangeLow"] == 105.0


def test_missing_market_uses_target():
    r = price(market=None)
    assert r["recommended"] == 115.0 and any("No market price" in w for w in r["warnings"])


def test_missing_cost_follows_market():
    r = price(cost=None)
    assert r["recommended"] == 112.0 and r["floorPrice"] is None and any("No purchases yet" in w for w in r["warnings"])


def test_nothing_known_gives_no_recommendation():
    r = price(cost=None, market=None)
    assert r["recommended"] is None and r["rangeLow"] is None and len(r["warnings"]) == 2


def test_what_if_margin_override():
    low, high = price(margin_pct=8, market=200.0), price(margin_pct=30, market=200.0)
    assert low["recommended"] == 108.0 and high["recommended"] == 130.0
    assert price(margin_pct=3, min_margin_pct=5, market=200.0)["recommended"] == 105.0     # target below floor -> floor wins


def test_current_price_warnings():
    assert any("below the market" in w for w in price(current_price=95.0)["warnings"])
    assert any("above the market" in w for w in price(current_price=130.0)["warnings"])
    assert not any("market" in w for w in price(current_price=112.0)["warnings"])
    r = price(current_price=120.0)
    assert r["gapToRecommendedPct"] == round((120 / 112 - 1) * 100, 1)


@pytest.mark.parametrize("x, unit, expected", [(112.26, "kg", 112.5), (112.24, "litre", 112.0), (47.4, "packet", 47.0), (47.5, "box", 48.0), (None, "kg", None)])
def test_rounding(x, unit, expected):
    assert round_price(x, unit) == expected


def test_packet_prices_are_whole_rupees():
    r = price(cost=20.0, market=22.7, unit="packet")
    assert r["recommended"] == float(int(r["recommended"]))


# ---------------------------------------------------------------- API
def _buy(client, d, qty, price_, date):
    client.post("/api/purchases", headers=d["headers"], json={"productId": d["product"]["id"], "supplierId": d["supplier"]["id"],
                "quantity": qty, "unitPrice": price_, "purchaseDate": date.isoformat()})


def test_api_uses_weighted_cost_of_last_5_and_retail_market(client, shop_with_data):
    d = shop_with_data
    _buy(client, d, 10, 500.0, TODAY - dt.timedelta(days=60))             # 6th-oldest purchase: must be ignored
    for i in range(5):
        _buy(client, d, 10 if i < 4 else 20, 40.0 if i < 4 else 41.0, TODAY - dt.timedelta(days=10 - i))
    r = client.get("/api/recommendations/selling-price", headers=d["headers"]).json()[0]
    assert r["costBasis"] == pytest.approx((4 * 10 * 40 + 20 * 41) / 60, abs=0.01)
    assert r["marketPrice"] == pytest.approx(44.8)                         # retail = 40 x 1.12 in the test data
    # cost 40.33 -> floor 42.35 (rounds to 42.5), target 46.38 (rounds to 46.5); market 44.8 lies between them
    assert r["floorPrice"] == 42.5 and r["targetPrice"] == 46.5 and r["recommended"] == 45.0
    assert r["currentPrice"] == 50                                         # the product's selling price
    assert any("above the market" in w for w in r["warnings"])


def test_api_margin_override_and_validation(client, shop_with_data):
    d = shop_with_data
    _buy(client, d, 10, 40.0, TODAY - dt.timedelta(days=2))
    default = client.get("/api/recommendations/selling-price", headers=d["headers"]).json()[0]
    wide = client.get(f"/api/recommendations/selling-price/{d['product']['id']}?targetMarginPct=40", headers=d["headers"]).json()
    assert wide["targetMarginPct"] == 40 and wide["targetPrice"] > default["targetPrice"]
    assert wide["recommended"] == default["recommended"] == 45.0         # the market (44.8) is inside both bands, so it is followed
    assert client.get("/api/recommendations/selling-price?targetMarginPct=500", headers=d["headers"]).status_code == 422


def test_api_no_purchases_falls_back_to_market(client, shop_with_data):
    r = client.get("/api/recommendations/selling-price", headers=shop_with_data["headers"]).json()[0]
    assert r["costBasis"] is None and r["recommended"] == 45.0 and any("No purchases" in w for w in r["warnings"])


def test_api_product_without_reference_commodity(client, register_user, create_shop, create_product):
    h = register_user()
    create_shop(h)
    p = create_product(h, "Soap")
    r = client.get(f"/api/recommendations/selling-price/{p['id']}", headers=h).json()
    assert r["recommended"] is None and r["marketPrice"] is None


def test_api_private_to_shop(client, shop_with_data, register_user, create_shop):
    h2 = register_user("z@test.com")
    create_shop(h2)
    assert client.get("/api/recommendations/selling-price", headers=h2).json() == []
    assert client.get(f"/api/recommendations/selling-price/{shop_with_data['product']['id']}", headers=h2).status_code == 404
