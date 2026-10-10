"""
conftest.py - shared pytest fixtures.

Every test gets a brand-new in-memory SQLite database (StaticPool = one shared connection),
and the FastAPI app is told to use it through a get_db override. Your real data is never touched.
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"            # set BEFORE the app is imported
os.environ.setdefault("SECRET_KEY", "test-secret")

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ReferencePrice
from app.services import cache

TODAY = dt.date.today()


# Run the whole suite on PostgreSQL:  TEST_DATABASE_URL=postgresql://user:pass@host/dbname pytest
# (the tables of that database are dropped and recreated for every test, use an EMPTY test database)
TEST_DB_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture()
def db():
    if TEST_DB_URL:
        engine = create_engine(TEST_DB_URL)
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()
    if TEST_DB_URL:
        Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def isolated_models(tmp_path, monkeypatch):
    """Tests never read or write the real trained models: they get an empty temporary models folder."""
    from app.ml import train_forecast
    from app.services import forecast_service
    folder = tmp_path / "models_store"
    monkeypatch.setattr(train_forecast, "MODEL_DIR", folder)
    monkeypatch.setattr(train_forecast, "EVAL_DIR", tmp_path / "eval")          # tests must never overwrite docs/eval/forecast_metrics.csv
    monkeypatch.setattr(forecast_service, "MODEL_DIR", folder)
    forecast_service.invalidate_forecasts()
    yield folder
    forecast_service.invalidate_forecasts()


@pytest.fixture()
def client(db):
    cache.clear_all()
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def register_user(client):
    """register_user(email) -> auth headers of a brand-new user."""
    def _register(email="owner@test.com", password="secret12", name="Test Owner"):
        r = client.post("/api/auth/signup", json={"fullName": name, "email": email, "password": password})
        assert r.status_code == 201, r.text
        return {"Authorization": "Bearer " + r.json()["access_token"]}
    return _register


@pytest.fixture()
def create_shop(client):
    def _create(headers, **kw):
        body = {"shopName": "Test Store", "shopType": "Kirana Store", "location": "Nagpur", **kw}
        r = client.post("/api/shop", json=body, headers=headers)
        assert r.status_code == 201, r.text
        return r.json()
    return _create


@pytest.fixture()
def create_product(client):
    def _create(headers, name="Rice", **kw):
        body = {"name": name, "category": "Grains", "unit": "kg", "openingStock": 0, "reorderLevel": 10, **kw}
        r = client.post("/api/products", json=body, headers=headers)
        assert r.status_code == 201, r.text
        return r.json()
    return _create


@pytest.fixture()
def create_supplier(client):
    def _create(headers, name="ABC Traders", **kw):
        r = client.post("/api/suppliers", json={"name": name, "contact": "9999999999", "address": "Nagpur", **kw}, headers=headers)
        assert r.status_code == 201, r.text
        return r.json()
    return _create


@pytest.fixture()
def add_reference(db):
    """add_reference('Rice', price=40, days=120) -> daily reference rows ending today (flat price unless a list is given)."""
    def _add(commodity="Rice", price=40.0, days=120, unit="kg"):
        for i in range(days):
            p = price[i] if isinstance(price, (list, tuple)) else price
            d = TODAY - dt.timedelta(days=days - 1 - i)
            db.add(ReferencePrice(commodity=commodity, market="All India", price_date=d, wholesale_price=p,
                                  retail_price=round(p * 1.12, 2), unit=unit, source="test"))
        db.commit()
    return _add


@pytest.fixture()
def shop_with_data(register_user, create_shop, create_product, create_supplier, add_reference):
    """A ready shop: Rice (linked to a flat Rs 40 market), one supplier, headers."""
    add_reference("Rice", 40.0, 120)
    h = register_user("data@test.com")
    shop = create_shop(h)
    product = create_product(h, "Rice", openingStock=0, referenceCommodity="Rice", sellingPrice=50)
    supplier = create_supplier(h, "ABC Traders", productIds=[product["id"]])
    return {"headers": h, "shop": shop, "product": product, "supplier": supplier}


@pytest.fixture(autouse=True)
def fresh_rate_limit():
    """Every test starts with an empty advisor rate-limit window."""
    from app.routers import advisor
    advisor.RATE_LIMIT.reset()
    advisor._timings.clear()
    yield
