"""
a_test_shop.py - tests for the shop API and shop scoping.

Run from backend/:   python -m pytest tests/a_test_shop.py -v
Uses an in-memory SQLite database, your real data is never touched.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.routers.auth import get_current_user
from app.database import Base, get_db
from app.routers import shop

EXPECTED_TABLES = {
    "users", "shops", "products", "suppliers", "supplier_products", "purchases", "sales",
    "reference_prices", "alerts", "activity_log", "advisor_messages", "model_metrics",
}


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    users = []
    for i in (1, 2):
        u = models.User(full_name=f"User {i}", email=f"user{i}@test.com", hashed_password="x")
        db.add(u)
        users.append(u)
    db.commit()

    current = {"user": users[0]}                       # which user is "logged in"
    app = FastAPI()
    app.include_router(shop.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current["user"]
    client = TestClient(app)
    yield client, current, users, db
    db.close()


def test_all_tables_exist():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_get_before_setup_is_404(env):
    client, *_ = env
    r = client.get("/api/shop")
    assert r.status_code == 404 and r.json()["detail"] == "Shop not set up yet"


def test_create_with_defaults_and_camelcase(env):
    client, *_ = env
    r = client.post("/api/shop", json={"shopName": "Sharma General Store", "location": "Nagpur"})
    assert r.status_code == 201
    body = r.json()
    assert body["shopName"] == "Sharma General Store"
    assert body["targetMarginPct"] == 15 and body["minMarginPct"] == 5
    assert body["leadTimeDays"] == 3 and body["coverDays"] == 14
    assert body["anomalyThresholdPct"] == 15 and body["zCutoff"] == 2.5 and body["language"] == "en"


def test_second_create_is_409(env):
    client, *_ = env
    client.post("/api/shop", json={"shopName": "A"})
    assert client.post("/api/shop", json={"shopName": "B"}).status_code == 409


def test_get_returns_created_shop(env):
    client, *_ = env
    client.post("/api/shop", json={"shopName": "A", "shopType": "Kirana"})
    r = client.get("/api/shop")
    assert r.status_code == 200 and r.json()["shopType"] == "Kirana"


def test_partial_update_changes_only_sent_fields(env):
    client, *_ = env
    client.post("/api/shop", json={"shopName": "A", "location": "Nagpur"})
    r = client.put("/api/shop", json={"targetMarginPct": 20, "language": "mr"})
    assert r.status_code == 200
    body = r.json()
    assert body["targetMarginPct"] == 20 and body["language"] == "mr"
    assert body["shopName"] == "A" and body["location"] == "Nagpur"      # untouched


@pytest.mark.parametrize("payload", [
    {"shopName": ""},                                  # empty name
    {"shopName": "A", "language": "fr"},               # unsupported language
    {"shopName": "A", "targetMarginPct": 150},         # margin above 100
    {"shopName": "A", "minMarginPct": 30, "targetMarginPct": 10},   # min > target
    {"shopName": "A", "zCutoff": 0},
])
def test_create_validation(env, payload):
    client, *_ = env
    assert client.post("/api/shop", json=payload).status_code == 422


def test_update_cannot_break_margin_rule(env):
    client, *_ = env
    client.post("/api/shop", json={"shopName": "A"})                   # min 5, target 15
    r = client.put("/api/shop", json={"minMarginPct": 25})             # 25 > 15 -> must fail
    assert r.status_code == 422
    assert client.get("/api/shop").json()["minMarginPct"] == 5          # unchanged after the failure


def test_shops_are_separate_per_user(env):
    client, current, users, _ = env
    client.post("/api/shop", json={"shopName": "Shop of user 1"})
    current["user"] = users[1]                                          # user 2 logs in
    assert client.get("/api/shop").status_code == 404                   # cannot see user 1's shop
    client.post("/api/shop", json={"shopName": "Shop of user 2"})
    assert client.get("/api/shop").json()["shopName"] == "Shop of user 2"
    client.put("/api/shop", json={"shopName": "Renamed by user 2"})
    current["user"] = users[0]
    assert client.get("/api/shop").json()["shopName"] == "Shop of user 1"   # user 1 unaffected


def test_user_id_in_body_is_ignored(env):
    client, _, users, _ = env
    r = client.post("/api/shop", json={"shopName": "A", "userId": users[1].id})
    assert r.json()["userId"] == users[0].id            # taken from the login, not the request
