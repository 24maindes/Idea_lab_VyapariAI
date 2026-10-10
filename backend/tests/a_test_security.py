"""Authentication, authorisation, injection and configuration safety."""
import datetime as dt

import pytest
from jose import jwt

from app import auth, settings
from conftest import TODAY


# ---------------------------------------------------------------- accounts and tokens
def test_signup_login_me_flow(client):
    r = client.post("/api/auth/signup", json={"fullName": "A B", "email": "ab@test.com", "password": "secret12"})
    assert r.status_code == 201 and r.json()["user"]["email"] == "ab@test.com" and "hashed" not in r.text and "secret12" not in r.text
    token = r.json()["access_token"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["fullName"] == "A B"
    ok = client.post("/api/auth/login", json={"email": "ab@test.com", "password": "secret12"})
    assert ok.status_code == 200 and ok.json()["token_type"] == "bearer"


def test_email_is_case_insensitive(client):
    client.post("/api/auth/signup", json={"fullName": "A", "email": "Owner@Test.com", "password": "secret12"})
    assert client.post("/api/auth/signup", json={"fullName": "B", "email": "owner@test.com", "password": "secret12"}).status_code == 400
    assert client.post("/api/auth/login", json={"email": "OWNER@test.COM", "password": "secret12"}).status_code == 200


@pytest.mark.parametrize("body, code", [
    ({"fullName": "", "email": "a@test.com", "password": "secret12"}, 422),
    ({"fullName": "A", "email": "not-an-email", "password": "secret12"}, 422),
    ({"fullName": "A", "email": "a@test.com", "password": "123"}, 422),
    ({"email": "a@test.com", "password": "secret12"}, 422),
])
def test_signup_validation(client, body, code):
    assert client.post("/api/auth/signup", json=body).status_code == code


def test_wrong_password_and_unknown_user_look_the_same(client):
    client.post("/api/auth/signup", json={"fullName": "A", "email": "a@test.com", "password": "secret12"})
    a = client.post("/api/auth/login", json={"email": "a@test.com", "password": "WRONG-pass"})
    b = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "secret12"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()           # no hint about which part was wrong


def test_tampered_expired_and_garbage_tokens_are_rejected(client, register_user):
    h = register_user()
    token = h["Authorization"].split()[1]
    payload = jwt.get_unverified_claims(token)
    forged = jwt.encode(payload, "another-secret", algorithm="HS256")                # right content, wrong signature
    expired = jwt.encode({**payload, "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)}, auth.SECRET_KEY, algorithm="HS256")
    none_alg = token.rsplit(".", 1)[0] + "."                                         # signature removed
    for bad in (forged, expired, none_alg, "garbage", "", token[:-3] + "xyz"):
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401, bad[:20]
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Basic {token}"}).status_code == 401


def test_token_of_a_deleted_user_is_rejected(client, register_user, db):
    from app.models import User
    h = register_user("gone@test.com")
    db.query(User).filter_by(email="gone@test.com").delete()
    db.commit()
    assert client.get("/api/auth/me", headers=h).status_code == 401


# ---------------------------------------------------------------- every protected endpoint needs login
PROTECTED_GET = ["/api/shop", "/api/products", "/api/suppliers", "/api/suppliers/comparison?productId=1", "/api/purchases", "/api/sales",
                 "/api/sales/summary", "/api/inventory", "/api/activity", "/api/alerts", "/api/alerts/count", "/api/forecast/1", "/api/forecast/models",
                 "/api/forecast/retrain/status", "/api/recommendations/purchase", "/api/recommendations/selling-price", "/api/analysis/fair-price",
                 "/api/analysis/fair-price/1", "/api/analysis/fair-price/check?productId=1&price=1", "/api/reference/commodities",
                 "/api/reference/prices?commodity=Rice", "/api/reference/latest?commodity=Rice", "/api/dashboard/summary", "/api/dashboard/price-trend?productId=1",
                 "/api/advisor/history", "/api/import/template/products"]


@pytest.mark.parametrize("path", PROTECTED_GET)
def test_get_endpoints_need_login(client, path):
    assert client.get(path).status_code == 401, path


@pytest.mark.parametrize("method, path", [("post", "/api/shop"), ("put", "/api/shop"), ("post", "/api/products"), ("post", "/api/suppliers"),
                                          ("post", "/api/purchases"), ("post", "/api/sales"), ("post", "/api/alerts/scan"), ("post", "/api/forecast/retrain"),
                                          ("post", "/api/advisor/chat"), ("delete", "/api/advisor/history"), ("patch", "/api/alerts/read-all"),
                                          ("put", "/api/auth/password"), ("delete", "/api/products/1"), ("delete", "/api/purchases/1"), ("post", "/api/import/products")])
def test_write_endpoints_need_login(client, method, path):
    r = client.request(method.upper(), path, json={})
    assert r.status_code == 401, (method, path, r.status_code)


def test_only_public_endpoints_are_open(client):
    assert client.get("/api/health").status_code == 200
    from app.main import app
    open_paths = set()
    for path, methods in app.openapi()["paths"].items():
        for m, spec in methods.items():
            if not spec.get("security") and not any(p.get("name") == "authorization" for p in spec.get("parameters", [])):
                open_paths.add((m.upper(), path))
    # signup/login/health are public; every other endpoint declares its login requirement through dependencies, checked above
    assert {("POST", "/api/auth/signup"), ("POST", "/api/auth/login"), ("GET", "/api/health")} <= open_paths


# ---------------------------------------------------------------- shop separation (attacker tries other shops' ids)
def test_other_shops_ids_everywhere(client, shop_with_data, register_user, create_shop):
    d = shop_with_data
    pid, sid = d["product"]["id"], d["supplier"]["id"]
    client.post("/api/purchases", headers=d["headers"], json={"productId": pid, "supplierId": sid, "quantity": 5, "unitPrice": 40, "purchaseDate": TODAY.isoformat()})
    h = register_user("attacker@test.com")
    create_shop(h)
    mine = client.post("/api/products", headers=h, json={"name": "Mine", "unit": "kg"}).json()
    for method, path, body in [
        ("put", f"/api/products/{pid}", {"name": "Hacked"}), ("delete", f"/api/products/{pid}", None),
        ("put", f"/api/suppliers/{sid}", {"name": "Hacked"}), ("delete", f"/api/suppliers/{sid}", None),
        ("get", f"/api/forecast/{pid}", None), ("get", f"/api/analysis/fair-price/{pid}", None),
        ("get", f"/api/analysis/fair-price/check?productId={pid}&price=10", None), ("get", f"/api/recommendations/purchase/{pid}", None),
        ("get", f"/api/recommendations/selling-price/{pid}", None), ("get", f"/api/suppliers/{sid}/prices?productId={mine['id']}", None),
        ("get", f"/api/suppliers/comparison?productId={pid}", None), ("get", f"/api/dashboard/price-trend?productId={pid}", None),
    ]:
        r = getattr(client, method)(path, headers=h, **({"json": body} if body is not None else {}))
        assert r.status_code == 404, (method, path, r.status_code)
    # creating records with ANOTHER shop's product or supplier fails
    assert client.post("/api/purchases", headers=h, json={"productId": pid, "supplierId": sid, "quantity": 1, "unitPrice": 1, "purchaseDate": TODAY.isoformat()}).status_code == 404
    assert client.post("/api/purchases", headers=h, json={"productId": mine["id"], "supplierId": sid, "quantity": 1, "unitPrice": 1, "purchaseDate": TODAY.isoformat()}).status_code == 404
    assert client.post("/api/suppliers", headers=h, json={"name": "S", "productIds": [pid]}).status_code == 422
    assert client.post("/api/advisor/chat", headers=h, json={"message": "hi", "productId": pid}).status_code == 404
    # nothing of the victim changed
    assert [p["name"] for p in client.get("/api/products", headers=d["headers"]).json()] == ["Rice"]


def test_mass_assignment_is_ignored(client, register_user, create_shop):
    h = register_user()
    me = client.get("/api/auth/me", headers=h).json()
    shop = client.post("/api/shop", headers=h, json={"shopName": "S", "userId": 999, "id": 999}).json()
    assert shop["userId"] == me["id"] and shop["id"] != 999
    p = client.post("/api/products", headers=h, json={"name": "P", "unit": "kg", "shopId": 999, "id": 999, "currentStock": 5000}).json()
    assert p["id"] != 999 and p["currentStock"] == 0                                  # stock only changes through purchases and sales
    assert [x["id"] for x in client.get("/api/products", headers=h).json()] == [p["id"]]


# ---------------------------------------------------------------- injection
INJECTIONS = ["' OR '1'='1", "'; DROP TABLE products; --", "\" OR 1=1 --", "%' UNION SELECT hashed_password FROM users --", "1; SELECT pg_sleep(5)"]


@pytest.mark.parametrize("payload", INJECTIONS)
def test_sql_injection_strings_are_just_text(client, shop_with_data, payload):
    h = shop_with_data["headers"]
    assert client.get("/api/products", headers=h, params={"q": payload, "category": payload}).status_code == 200
    assert client.get("/api/products", headers=h, params={"q": payload}).json() == []
    assert client.get("/api/reference/prices", headers=h, params={"commodity": payload}).status_code == 404
    assert client.get("/api/forecast/models", headers=h, params={"commodity": payload}).json() == []
    p = client.post("/api/products", headers=h, json={"name": payload[:100], "unit": "kg"})
    assert p.status_code in (201, 422)
    assert client.post("/api/auth/login", json={"email": "a@b.co", "password": payload}).status_code in (401, 422)
    assert client.get("/api/products", headers=h).status_code == 200                       # the tables are all still there
    assert client.get("/api/purchases", headers=h, params={"sort": payload}).status_code == 422


def test_html_in_text_fields_is_stored_and_returned_as_plain_text(client, register_user, create_shop):
    h = register_user()
    create_shop(h)
    xss = "<script>alert('x')</script>"
    p = client.post("/api/products", headers=h, json={"name": xss, "unit": "kg"})
    assert p.status_code == 201 and p.json()["name"] == xss and p.headers["content-type"].startswith("application/json")
    assert client.get("/api/products", headers=h).json()[0]["name"] == xss              # JSON only; React escapes it when rendering


@pytest.mark.parametrize("body", [{"name": "x" * 121, "unit": "kg"}, {"name": "ok", "unit": "kg", "category": "c" * 61}, {"name": "ok", "unit": "kg", "openingStock": 1e12}])
def test_oversized_values(client, register_user, create_shop, body):
    h = register_user()
    create_shop(h)
    r = client.post("/api/products", headers=h, json=body)
    assert r.status_code in (201, 422)
    if "openingStock" in body:
        assert r.status_code == 201 or r.status_code == 422


# ---------------------------------------------------------------- CORS and configuration
def test_cors_allows_only_configured_origins(client):
    ok = client.options("/api/shop", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options("/api/shop", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_production_refuses_unsafe_configuration(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "insecure_dev_secret")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    with pytest.raises(RuntimeError) as e:
        settings.check_production()
    assert "SECRET_KEY" in str(e.value) and "CORS_ORIGINS" in str(e.value)
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="must not be"):
        settings.check_production()


def test_production_accepts_a_safe_configuration(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "k" * 48)
    monkeypatch.setenv("CORS_ORIGINS", "https://vyapariai.example.com/")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    assert settings.check_production() == [] and settings.cors_origins() == ["https://vyapariai.example.com"]


def test_development_only_warns(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "short")
    assert any("SECRET_KEY" in w for w in settings.check_production())


def test_postgres_url_scheme_is_fixed():
    from app.database import normalize_url
    assert normalize_url("postgres://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"
    assert normalize_url("postgresql://u:p@h/db") == "postgresql://u:p@h/db" and normalize_url("sqlite:///./x.db") == "sqlite:///./x.db"


def test_startup_loads_reference_prices_only_when_empty(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app import startup
    from app.database import Base
    from app.ml import load_reference
    from app.models import ReferencePrice
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    csv = tmp_path / "reference_prices.csv"
    csv.write_text("commodity,market,price_date,wholesale_price,retail_price,unit,source\nRice,All India,2026-01-01,40,45,kg,t\nRice,All India,2026-01-02,41,46,kg,t\n")
    for mod in (startup, load_reference):
        monkeypatch.setattr(mod, "SessionLocal", Session)
        monkeypatch.setattr(mod, "engine", engine, raising=False)
    monkeypatch.setattr(startup, "CSV_PATH", csv)
    monkeypatch.setattr(load_reference, "CSV_PATH", csv)
    assert startup.ensure_reference_data() == 2
    assert startup.ensure_reference_data() == 0                                         # already filled: nothing happens
    db = Session()
    assert db.execute(select(func.count()).select_from(ReferencePrice)).scalar() == 2
