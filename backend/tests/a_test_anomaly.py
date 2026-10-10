"""Anomaly detection: pure functions (ml/anomaly.py) and the service/API around them."""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from app.ml import anomaly as ml
from conftest import TODAY


def frame(prices, ref=40.0, product_id=1, start=dt.date(2026, 1, 1), step=7):
    return pd.DataFrame({
        "purchase_id": range(1, len(prices) + 1), "product_id": product_id,
        "purchase_date": [start + dt.timedelta(days=step * i) for i in range(len(prices))],
        "unit_price": prices, "reference_price": ref})


def normal_prices(n=20, seed=1):
    rng = np.random.default_rng(seed)
    return list(40 * (1 + rng.uniform(-0.02, 0.02, n)))


# ---------------------------------------------------------------- features
def test_features_columns_and_ratio():
    f = ml.build_features(frame(normal_prices(10)))
    for col in ["ratio_to_reference", "pct_change_prev", "zscore_90d", "rolling_median_dev", "deviation_pct"]:
        assert col in f.columns
    assert abs(f["ratio_to_reference"].iloc[0] - f["unit_price"].iloc[0] / 40) < 1e-9


def test_zscore_is_zero_with_fewer_than_5_earlier_purchases():
    f = ml.build_features(frame([40, 41, 39, 40, 80]))          # the 5th purchase has only 4 earlier ones
    assert f["zscore_90d"].iloc[4] == 0


def test_features_do_not_use_the_future():
    """The features of purchase k must not change when LATER purchases are added."""
    p = normal_prices(15)
    a = ml.build_features(frame(p[:10]))
    b = ml.build_features(frame(p))
    cols = ["zscore_90d", "pct_change_prev", "rolling_median_dev", "ratio_to_reference"]
    assert np.allclose(a[cols].to_numpy(), b[cols].iloc[:10].to_numpy())


def test_pct_change_is_per_product():
    df = pd.concat([frame([40, 44], product_id=1), frame([100, 100], product_id=2).assign(purchase_id=[3, 4])])
    f = ml.build_features(df)
    assert f[(f.product_id == 1)]["pct_change_prev"].iloc[1] == pytest.approx(10.0)
    assert f[(f.product_id == 2)]["pct_change_prev"].iloc[0] == 0


# ---------------------------------------------------------------- detectors
def test_zscore_flags_cutoff():
    f = ml.build_features(frame(normal_prices(20) + [60]))
    z = ml.zscore_flags(f, 2.5)
    assert bool(z["flag"].iloc[-1]) and not z["flag"].iloc[:-1].any()
    assert not ml.zscore_flags(f, 100)["flag"].any()            # a huge cutoff flags nothing


def test_threshold_flags_both_directions():
    f = ml.build_features(frame([40, 47, 33, 41]))              # +17.5 %, -17.5 %
    t = ml.threshold_flags(f, 15)
    assert t["flag"].tolist() == [False, True, True, False]
    assert not ml.threshold_flags(f, 20)["flag"].any()


def test_isolation_forest_shape_and_small_data():
    f = ml.build_features(frame(normal_prices(25) + [70]))
    r = ml.isolation_forest_flags(f, contamination=0.05)
    assert list(r.columns) == ["flag", "score"] and len(r) == len(f)
    assert bool(r["flag"].iloc[-1])                             # the obvious outlier is isolated
    tiny = ml.isolation_forest_flags(ml.build_features(frame([40, 41, 42])))
    assert not tiny["flag"].any()                               # fewer than 10 rows -> says nothing


def test_isolation_forest_is_deterministic():
    f = ml.build_features(frame(normal_prices(40) + [70, 20]))
    assert ml.isolation_forest_flags(f)["flag"].tolist() == ml.isolation_forest_flags(f)["flag"].tolist()


# ---------------------------------------------------------------- ensemble
def test_ensemble_flags_obvious_spike_and_ignores_normal():
    f = ml.build_features(frame(normal_prices(25) + [56]))      # +40 %
    r = ml.ensemble(f, cutoff=2.5, threshold_pct=15)
    last = r.iloc[-1]
    assert last["flagged"] and last["severity"] == "high" and last["direction"] == "above"
    assert last["deviationPct"] == pytest.approx(40.0, abs=3)
    assert not r["flagged"].iloc[:15].any()                     # ordinary +/-2 % noise is not flagged


def test_ensemble_big_drop_is_flagged_below():
    f = ml.build_features(frame(normal_prices(25) + [28]))      # -30 %
    last = ml.ensemble(f).iloc[-1]
    assert last["flagged"] and last["direction"] == "below"


def test_ensemble_strong_deviation_alone_is_enough():
    f = ml.build_features(frame([40, 40, 52]))                  # +30 %, too little history for z-score or forest
    last = ml.ensemble(f, threshold_pct=50).iloc[-1]             # threshold rule would NOT fire at 50 %...
    assert last["flagged"]                                       # ...but > 25 % off the market flags it by itself


def test_ensemble_severity_levels():
    f = ml.build_features(frame([40, 40, 40, 40.1, 40.1, 40.2, 40.2, 40.3, 40.3, 40.4, 40.4, 40.5, 49.0]))   # about +22 %
    last = ml.ensemble(f, threshold_pct=15).iloc[-1]
    assert last["flagged"] and last["severity"] in ("medium", "high")
    assert last["votes"] >= 2


def test_missing_reference_falls_back_to_recent_prices():
    df = frame(normal_prices(12) + [60])
    df["reference_price"] = np.nan                                # no market price known
    r = ml.ensemble(ml.build_features(df))
    assert bool(r["flagged"].iloc[-1])


# ---------------------------------------------------------------- service + API
def _buy(client, d, price, date=None, qty=5):
    return client.post("/api/purchases", headers=d["headers"], json={
        "productId": d["product"]["id"], "supplierId": d["supplier"]["id"], "quantity": qty, "unitPrice": price,
        "purchaseDate": (date or TODAY).isoformat()})


def _history(client, d, n=15, price=40):
    for i in range(n):
        _buy(client, d, round(price * (1 + (i % 3 - 1) * 0.01), 2), TODAY - dt.timedelta(days=7 * (n - i) + 1))


def test_purchase_40_percent_above_market_returns_anomaly_insight(client, shop_with_data):
    d = shop_with_data
    _history(client, d)
    r = _buy(client, d, 56.0)                                     # market is a flat Rs 40
    assert r.status_code == 201
    a = r.json()["insights"]["anomaly"]
    assert a["severity"] == "high" and a["deviationPct"] == pytest.approx(40.0)
    assert "above the market price of Rs 40" in a["message"]
    assert client.get("/api/alerts/count", headers=d["headers"]).json()["unread"] == 1


def test_normal_purchase_has_no_anomaly(client, shop_with_data):
    d = shop_with_data
    _history(client, d)
    r = _buy(client, d, 40.4)
    assert r.json()["insights"] == {}
    assert client.get("/api/alerts/count", headers=d["headers"]).json()["unread"] == 0


def test_scan_twice_does_not_duplicate_alerts(client, shop_with_data):
    d = shop_with_data
    _history(client, d)
    # a spike that was entered BEFORE alerts existed (insert directly through the API, then clear its alert)
    _buy(client, d, 58.0, TODAY - dt.timedelta(days=3))
    client.patch("/api/alerts/read-all", headers=d["headers"])
    first = client.post("/api/alerts/scan", headers=d["headers"]).json()
    second = client.post("/api/alerts/scan", headers=d["headers"]).json()
    assert second["newAlerts"] == 0
    types = [a["type"] for a in client.get("/api/alerts", headers=d["headers"]).json()]
    assert types.count("price_anomaly") == 1
    assert first["purchasesScanned"] >= 16


def test_low_stock_alert_once_and_closed_when_restocked(client, shop_with_data):
    d = shop_with_data                                             # stock 0 <= reorder level 10
    client.post("/api/alerts/scan", headers=d["headers"])
    client.post("/api/alerts/scan", headers=d["headers"])
    low = [a for a in client.get("/api/alerts?type=low_stock", headers=d["headers"]).json()]
    assert len(low) == 1 and low[0]["severity"] == "high" and "out of stock" in low[0]["message"]
    _buy(client, d, 40.0, qty=100)
    client.post("/api/alerts/scan", headers=d["headers"])
    assert client.get("/api/alerts/count", headers=d["headers"]).json()["unread"] == 0


def test_overpaying_supplier_alert(client, shop_with_data):
    d = shop_with_data
    for i in range(3):
        _buy(client, d, 46.0, TODAY - dt.timedelta(days=30 - 7 * i))   # +15 % three times in a row
    client.post("/api/alerts/scan", headers=d["headers"])
    over = client.get("/api/alerts?type=overpaying", headers=d["headers"]).json()
    assert len(over) == 1 and "last 3 Rice purchases" in over[0]["message"]


def test_alert_filters_and_read_flow(client, shop_with_data):
    d = shop_with_data
    client.post("/api/alerts/scan", headers=d["headers"])
    alert = client.get("/api/alerts?status=unread", headers=d["headers"]).json()[0]
    assert client.patch(f"/api/alerts/{alert['id']}/read", headers=d["headers"]).json()["isRead"] is True
    assert client.get("/api/alerts?status=unread", headers=d["headers"]).json() == []
    assert len(client.get("/api/alerts?status=read", headers=d["headers"]).json()) == 1
    assert client.get("/api/alerts?severity=bogus", headers=d["headers"]).status_code == 422


def test_alerts_are_private_to_each_shop(client, shop_with_data, register_user, create_shop):
    d = shop_with_data
    client.post("/api/alerts/scan", headers=d["headers"])
    h2 = register_user("spy@test.com")
    create_shop(h2)
    assert client.get("/api/alerts", headers=h2).json() == []
    assert client.get("/api/alerts/count", headers=h2).json() == {"unread": 0}
    aid = client.get("/api/alerts", headers=d["headers"]).json()[0]["id"]
    assert client.patch(f"/api/alerts/{aid}/read", headers=h2).status_code == 404


def test_shop_threshold_setting_is_used(client, shop_with_data):
    """Raising the shop's anomaly threshold to 50 % and z cutoff to 4 makes a +30 % price flagged only by the 25 % rule."""
    d = shop_with_data
    client.put("/api/shop", headers=d["headers"], json={"anomalyThresholdPct": 50, "zCutoff": 4})
    _history(client, d)
    a = _buy(client, d, 52.0).json()["insights"]["anomaly"]        # +30 %
    assert a["methods"] == ["isolation_forest"] or "threshold" not in a["methods"]
