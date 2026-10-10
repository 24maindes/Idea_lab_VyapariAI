"""
b_test_fair_price.py
--------------------
Tests for services/fair_price.py and routers/analysis.py.

Run from the backend folder (the file name does not start with test_, so name it explicitly):
    python -m pytest tests/b_test_fair_price.py -v

Uses a throw-away in-memory SQLite database, so your real data is never touched.
"""
import datetime as dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.routers.auth import get_current_user
from app.database import Base, get_db
from app.ml.seed_demo import build          # tolerant constructor (works with small column-name differences)
from app.routers import analysis
from app.services.fair_price import (get_reference_price, product_fair_price, variance_pct, verdict)

TODAY = dt.date(2026, 10, 1)


# ================================================================ pure functions (no database)
@pytest.mark.parametrize("variance, expected", [
    (-10.0, "Great deal"),
    (-3.1, "Great deal"),
    (-3.0, "Great deal"),      # boundary: -3 is still a great deal
    (-2.9, "Fair"),
    (0.0, "Fair"),
    (3.0, "Fair"),             # boundary: 3 is still fair
    (3.1, "Slightly high"),
    (8.0, "Slightly high"),    # boundary: 8 is still slightly high
    (8.1, "Overpaying"),
    (40.0, "Overpaying"),
])
def test_verdict_boundaries(variance, expected):
    assert verdict(variance) == expected


def test_verdict_none():
    assert verdict(None) is None


def test_variance_math():
    assert variance_pct(48, 45) == 6.7        # (48-45)/45 = 6.666...
    assert variance_pct(43, 45) == -4.4
    assert variance_pct(45, 45) == 0.0
    assert variance_pct(103, 100) == 3.0      # so 3.0 shown on screen = "Fair", consistent


def test_variance_missing_or_bad_reference():
    assert variance_pct(48, None) is None
    assert variance_pct(48, 0) is None
    assert variance_pct(None, 45) is None


# ================================================================ database fixtures
@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()


def make_shop(db, email="a@test.com"):
    user = build(models.User, email=email, hashed_password="x", full_name="T")
    db.add(user)
    db.flush()
    shop = build(models.Shop, owner_id=user.id, shop_name="Test Shop", location="Nagpur")
    db.add(shop)
    db.flush()
    return user, shop


def add_ref(db, commodity, date, price):
    db.add(models.ReferencePrice(commodity=commodity, market="All India", price_date=date,
                                 wholesale_price=price, retail_price=price * 1.1, unit="kg", source="test"))


def add_purchase(db, shop, product, supplier, date, price, qty=10):
    db.add(build(models.Purchase, shop_id=shop.id, product_id=product.id, supplier_id=supplier.id,
                 quantity=qty, unit_price=price, purchase_date=date))


@pytest.fixture()
def world(db):
    """One shop, product linked to 'Rice', two suppliers, market price flat at Rs 100."""
    user, shop = make_shop(db)
    product = build(models.Product, shop_id=shop.id, name="Rice", category="Grains", unit="kg",
                    reference_commodity="Rice", current_stock=0, reorder_level=10)
    abc = build(models.Supplier, shop_id=shop.id, name="ABC Traders")
    sharma = build(models.Supplier, shop_id=shop.id, name="Sharma Foods")
    db.add_all([product, abc, sharma])
    db.flush()
    for i in range(60):
        add_ref(db, "Rice", TODAY - dt.timedelta(days=i), 100.0)
    # ABC pays 98 (-2 %), Sharma pays 106 (+6 %)
    add_purchase(db, shop, product, abc, TODAY - dt.timedelta(days=20), 98, qty=10)
    add_purchase(db, shop, product, sharma, TODAY - dt.timedelta(days=10), 106, qty=20)
    db.commit()
    return user, shop, product, abc, sharma


# ================================================================ reference lookup
def test_reference_lookback_window(db):
    add_ref(db, "Rice", TODAY - dt.timedelta(days=7), 90.0)
    db.commit()
    # exactly 7 days old -> still used
    assert get_reference_price(db, "Rice", TODAY) == 90.0
    # 8 days old -> too old
    assert get_reference_price(db, "Rice", TODAY + dt.timedelta(days=1)) is None


def test_reference_uses_latest_row_on_or_before_date(db):
    add_ref(db, "Rice", TODAY - dt.timedelta(days=3), 90.0)
    add_ref(db, "Rice", TODAY - dt.timedelta(days=1), 95.0)
    add_ref(db, "Rice", TODAY + dt.timedelta(days=1), 999.0)      # future row must be ignored
    db.commit()
    assert get_reference_price(db, "Rice", TODAY) == 95.0
    assert get_reference_price(db, "Rice", TODAY - dt.timedelta(days=2)) == 90.0


def test_reference_kind_retail(db):
    add_ref(db, "Rice", TODAY, 100.0)
    db.commit()
    assert get_reference_price(db, "Rice", TODAY, kind="retail") == pytest.approx(110.0)


def test_reference_no_commodity(db):
    assert get_reference_price(db, None, TODAY) is None
    assert get_reference_price(db, "Unknown", TODAY) is None


# ================================================================ product analysis
def test_supplier_breakdown_signs(db, world):
    _, shop, product, *_ = world
    d = product_fair_price(db, shop, product, days=180, today=TODAY)
    by_name = {b["supplier"]: b["avgVariancePct"] for b in d["supplierBreakdown"]}
    assert by_name["ABC Traders"] == -2.0          # slightly negative
    assert by_name["Sharma Foods"] == 6.0          # positive
    assert d["hasMarketData"] is True


def test_last_purchase_and_verdict(db, world):
    _, shop, product, *_ = world
    d = product_fair_price(db, shop, product, days=180, today=TODAY)
    assert d["lastPurchasePrice"] == 106.0         # Sharma, 10 days ago
    assert d["referencePrice"] == 100.0
    assert d["variancePct"] == 6.0
    assert d["verdict"] == "Slightly high"


def test_potential_savings_counts_only_purchases_above_market(db, world):
    _, shop, product, *_ = world
    d = product_fair_price(db, shop, product, days=180, today=TODAY)
    # Only the Sharma purchase is above market: (106-100) x 20 kg = 120. ABC (98) adds nothing.
    assert d["potentialSavings"] == 120.0
    assert d["overspend90Days"] == 120.0


def test_weighted_30_day_average(db, world):
    _, shop, product, *_ = world
    d = product_fair_price(db, shop, product, days=180, today=TODAY)
    assert d["avg30DayPrice"] == round((98 * 10 + 106 * 20) / 30, 2)


def test_points_and_series(db, world):
    _, shop, product, *_ = world
    d = product_fair_price(db, shop, product, days=180, today=TODAY)
    assert len(d["points"]) == 2
    assert {"date", "price", "supplier", "variancePct"} <= set(d["points"][0])
    assert len(d["series"]) > 0 and d["series"][0]["referencePrice"] == 100.0


def test_missing_data_no_commodity(db):
    """Product without reference_commodity -> hasMarketData False, no crash."""
    _, shop = make_shop(db)
    product = build(models.Product, shop_id=shop.id, name="Soap", unit="packet", reference_commodity=None,
                    current_stock=0, reorder_level=5)
    sup = build(models.Supplier, shop_id=shop.id, name="S")
    db.add_all([product, sup])
    db.flush()
    add_purchase(db, shop, product, sup, TODAY - dt.timedelta(days=5), 30)
    db.commit()
    d = product_fair_price(db, shop, product, days=180, today=TODAY)
    assert d["hasMarketData"] is False
    assert d["lastPurchasePrice"] == 30.0          # own data still shown
    assert d["referencePrice"] is None and d["variancePct"] is None and d["verdict"] is None
    assert d["series"] == [] and d["potentialSavings"] == 0


def test_missing_data_commodity_without_rows(db):
    _, shop = make_shop(db)
    product = build(models.Product, shop_id=shop.id, name="Ghost", unit="kg", reference_commodity="Nope",
                    current_stock=0, reorder_level=5)
    db.add(product)
    db.commit()
    d = product_fair_price(db, shop, product, days=180, today=TODAY)
    assert d["hasMarketData"] is False
    assert d["lastPurchasePrice"] is None


# ================================================================ API (auth stubbed, in-memory db)
@pytest.fixture()
def client(db, world):
    user, *_ = world
    app = FastAPI()
    app.include_router(analysis.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_api_summary_has_one_row_per_product(client):
    r = client.get("/api/analysis/fair-price")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1 and rows[0]["productName"] == "Rice"
    assert "variancePct" in rows[0] and "hasMarketData" in rows[0]      # camelCase keys


def test_api_detail_camelcase_keys(client, world):
    _, _, product, *_ = world
    d = client.get(f"/api/analysis/fair-price/{product.id}?days=180").json()
    for key in ("avg30DayPrice", "overspend90Days", "supplierBreakdown", "series", "points"):
        assert key in d


def test_api_check_message(client, world):
    _, _, product, *_ = world
    r = client.get("/api/analysis/fair-price/check", params={"productId": product.id, "price": 106,
                                                              "date": TODAY.isoformat()})
    assert r.status_code == 200
    body = r.json()
    assert body["variancePct"] == 6.0 and body["verdict"] == "Slightly high"
    assert body["message"] == "Rs 106 is 6.0% above the market price of Rs 100 on 01 Oct 2026"


def test_api_check_no_market_data_is_not_an_error(client, world):
    _, _, product, *_ = world
    r = client.get("/api/analysis/fair-price/check", params={"productId": product.id, "price": 50,
                                                              "date": "2015-01-01"})
    assert r.status_code == 200 and r.json()["hasMarketData"] is False


def test_api_check_rejects_bad_price(client, world):
    _, _, product, *_ = world
    assert client.get("/api/analysis/fair-price/check", params={"productId": product.id, "price": 0}).status_code == 422


def test_api_other_shops_product_is_hidden(db, client):
    """A product of ANOTHER shop must look like 'not found' (shop scoping)."""
    _, other_shop = make_shop(db, email="other@test.com")
    other = build(models.Product, shop_id=other_shop.id, name="Secret", unit="kg", reference_commodity="Rice",
                  current_stock=0, reorder_level=1)
    db.add(other)
    db.commit()
    assert client.get(f"/api/analysis/fair-price/{other.id}").status_code == 404
    assert client.get("/api/analysis/fair-price/check", params={"productId": other.id, "price": 10}).status_code == 404
    names = [r["productName"] for r in client.get("/api/analysis/fair-price").json()]
    assert "Secret" not in names
