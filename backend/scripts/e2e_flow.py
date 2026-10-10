"""
e2e_flow.py - end-to-end check of a RUNNING server, with timings.

    1. python -m uvicorn app.main:app           (reference prices loaded, models trained)
    2. python scripts/e2e_flow.py               (from the backend folder)   [API_URL=https://... to test a hosted server]

It signs up a random new user and walks through the whole product: shop, 3 products, 2 suppliers, 6 purchases (one at an abnormal
price), 10 sales, then fair-price, forecast, recommendations, dashboard, alerts and the advisor. Prints PASS/FAIL and the response
time of every step and writes docs/eval/e2e_timings.json (used by make_eval_docs.py for docs/eval/performance.md).
Exit code 0 only if every step passed.
"""
import datetime as dt
import json
import os
import random
import sys
import time
from pathlib import Path

import requests

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")
OUT = Path(__file__).resolve().parents[2] / "docs" / "eval" / "e2e_timings.json"
today = dt.date.today()
day = lambda n: (today - dt.timedelta(days=n)).isoformat()      # noqa: E731

results: list[dict] = []
state: dict = {}


def step(name, fn):
    t0 = time.perf_counter()
    try:
        detail = fn()
        ok, msg = True, detail or ""
    except Exception as e:                                       # noqa: BLE001 - report every failure, keep going
        ok, msg = False, f"{type(e).__name__}: {e}"
    ms = (time.perf_counter() - t0) * 1000
    results.append({"step": name, "ok": ok, "ms": round(ms, 1), "detail": msg})
    print(f"[{'PASS' if ok else 'FAIL'}] {name:<46} {ms:7.0f} ms  {msg}")


def api(method, path, expect=(200, 201), **kw):
    r = requests.request(method, BASE + path, headers=state.get("headers", {}), timeout=90, **kw)
    if r.status_code not in expect:
        raise AssertionError(f"{method} {path} -> {r.status_code} {r.text[:200]}")
    return r.json() if r.content else None


def main() -> None:
    email = f"e2e{random.randint(100000, 999999)}@test.com"

    def signup():
        r = api("POST", "/api/auth/signup", json={"fullName": "E2E Tester", "email": email, "password": "secret123"})
        state["headers"] = {"Authorization": "Bearer " + r["access_token"]}
        return email
    step("signup a new user", signup)
    if "headers" not in state:
        sys.exit("Cannot continue without a login. Is the server running?")

    step("create shop", lambda: api("POST", "/api/shop", json={"shopName": "E2E Store", "shopType": "Kirana Store", "location": "Nagpur"})["shopName"])

    def products():
        for name, comm, price in (("Rice", "Rice", 48), ("Sugar", "Sugar", 47), ("Onion", "Onion", 32)):
            p = api("POST", "/api/products", json={"name": name, "category": "Staples", "unit": "kg", "openingStock": 20, "reorderLevel": 30,
                                                   "sellingPrice": price, "referenceCommodity": comm})
            state[name] = p["id"]
        return "3 products"
    step("create 3 products linked to market data", products)

    def suppliers():
        for name in ("ABC Traders", "XYZ Wholesale"):
            state[name] = api("POST", "/api/suppliers", json={"name": name, "contact": "9999999999", "productIds": [state["Rice"], state["Sugar"], state["Onion"]]})["id"]
        return "2 suppliers"
    step("create 2 suppliers", suppliers)

    def purchases():
        market = {p["name"]: api("GET", f"/api/reference/latest?commodity={p['name']}")["wholesalePrice"] for p in ({"name": "Rice"}, {"name": "Sugar"}, {"name": "Onion"})}
        plan = [("Rice", "ABC Traders", 1.00, 40, 21), ("Rice", "XYZ Wholesale", 1.02, 40, 14), ("Sugar", "ABC Traders", 0.99, 30, 12),
                ("Sugar", "XYZ Wholesale", 1.01, 30, 6), ("Onion", "ABC Traders", 1.00, 50, 9), ("Onion", "XYZ Wholesale", 1.42, 50, 2)]   # last one: +42 %
        for prod, sup, factor, qty, ago in plan:
            r = api("POST", "/api/purchases", json={"productId": state[prod], "supplierId": state[sup], "quantity": qty,
                                                    "unitPrice": round(market[prod] * factor, 2), "purchaseDate": day(ago)})
            if factor > 1.3:
                state["anomaly"] = r["insights"].get("anomaly")
        return "6 purchases"
    step("record 6 purchases (one 42 % above market)", purchases)

    step("abnormal purchase flagged at once", lambda: (_ for _ in ()).throw(AssertionError("no anomaly insight returned")) if not state.get("anomaly") else state["anomaly"]["severity"])

    def sales():
        for i in range(10):
            api("POST", "/api/sales", json={"productId": state[("Rice", "Sugar", "Onion")[i % 3]], "quantity": 4, "saleDate": day(9 - i)})
        return "10 sales"
    step("record 10 sales", sales)

    step("fair price - all products", lambda: f"{len(api('GET', '/api/analysis/fair-price'))} rows")
    step("fair price - one product (detail)", lambda: api("GET", f"/api/analysis/fair-price/{state['Rice']}")["verdict"])
    step("fair price - live check", lambda: api("GET", f"/api/analysis/fair-price/check?productId={state['Rice']}&price=60")["message"])

    def forecast():
        f = api("GET", f"/api/forecast/{state['Rice']}?horizon=7")
        assert f["available"], f.get("reason")
        return f"{f['modelName']} {f['changePct']:+.1f}% {f['direction']}"
    step("forecast (7 days)", forecast)
    step("forecast model comparison", lambda: f"{len(api('GET', '/api/forecast/models?commodity=Rice'))} models")

    def buy_recs():
        recs = api("GET", "/api/recommendations/purchase")
        assert len(recs) == 3 and all(r["reasons"] for r in recs)
        return ", ".join(f"{r['productName']}:{r['action']}" for r in recs)
    step("recommendations - what to buy", buy_recs)
    step("recommendations - selling price", lambda: ", ".join(f"{r['productName']} {r['recommended']}" for r in api("GET", "/api/recommendations/selling-price")))
    step("suppliers - comparison", lambda: f"{len(api('GET', f'/api/suppliers/comparison?productId={state['Rice']}')['suppliers'])} suppliers")
    step("alerts - scan and list", lambda: (api("POST", "/api/alerts/scan"), f"{len(api('GET', '/api/alerts'))} alerts")[1])
    step("inventory", lambda: f"{len(api('GET', '/api/inventory'))} rows")

    def dashboard():
        s = api("GET", "/api/dashboard/summary")
        assert s["totalProducts"] == 3 and s["purchasesThisMonth"]["count"] >= 0
        return f"{len(s['topRecommendations'])} recommendations, {s['unreadAlerts']} unread alerts"
    step("dashboard summary", dashboard)
    step("dashboard price trend", lambda: f"{len(api('GET', f'/api/dashboard/price-trend?productId={state['Rice']}')['history'])} days")

    def advisor():
        a = api("POST", "/api/advisor/chat", json={"message": "Is the price I paid for rice fair?", "language": "en"})
        assert a["answer"] and a["sources"]
        return ("offline fallback" if a["usedFallback"] else "AI") + f", {len(a['sources'])} sources"
    step("advisor chat", advisor)
    step("advisor chat (Hindi)", lambda: ("offline fallback" if (r := api("POST", "/api/advisor/chat", json={"message": "चावल का भाव सही है?", "language": "hi"}))["usedFallback"] else "AI") + f", {len(r['answer'])} chars")

    def isolation():
        other = requests.post(BASE + "/api/auth/signup", json={"fullName": "Other", "email": "o" + email, "password": "secret123"}, timeout=30).json()
        h = {"Authorization": "Bearer " + other["access_token"]}
        requests.post(BASE + "/api/shop", json={"shopName": "Other Shop"}, headers=h, timeout=30)
        if requests.get(BASE + "/api/products", headers=h, timeout=30).json():
            raise AssertionError("another shop can see these products")
        if requests.get(BASE + f"/api/forecast/{state['Rice']}", headers=h, timeout=30).status_code != 404:
            raise AssertionError("another shop can read this product's forecast")
        return "isolated"
    step("another user cannot see this shop's data", isolation)

    failed = [r for r in results if not r["ok"]]
    print(f"\n{len(results) - len(failed)}/{len(results)} steps passed; slowest: " + ", ".join(f"{r['step']} ({r['ms']:.0f} ms)" for r in sorted(results, key=lambda r: -r["ms"])[:3]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"date": today.isoformat(), "server": BASE, "steps": results}, indent=2), encoding="utf-8")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
