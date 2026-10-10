"""Forecasting: features (no leakage), training/selection, forecast service and API."""
import datetime as dt

import joblib
import numpy as np
import pandas as pd
import pytest

from app.ml import features as F
from app.ml import train_forecast as T
from app.models import ModelMetric
from app.services import forecast_service as FS
from conftest import TODAY


def make_series(n=260, base=40.0, drift=0.0004, seed=3) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(end=pd.Timestamp(TODAY), periods=n, freq="D")
    wave = 1 + 0.03 * np.sin(2 * np.pi * np.arange(n) / 90)
    return pd.Series(base * (1 + drift) ** np.arange(n) * wave * np.exp(rng.normal(0, 0.004, n)), index=idx)


# ---------------------------------------------------------------- features
def test_feature_columns_and_no_nans():
    f = F.build_features(make_series())
    assert list(f.columns) == F.FEATURES + ["target"]
    assert not f.isna().any().any()
    assert len(F.FEATURES) == 14


def test_features_use_only_past_data():
    """Changing TODAY's price must not change any of today's features (they only see yesterday and earlier)."""
    s = make_series(120)
    s2 = s.copy()
    s2.iloc[-1] = s2.iloc[-1] * 3
    a, b = F.build_features(s), F.build_features(s2)
    assert np.allclose(a[F.FEATURES].iloc[-1].to_numpy(), b[F.FEATURES].iloc[-1].to_numpy())
    assert a["target"].iloc[-1] != b["target"].iloc[-1]


def test_lag_and_rolling_values_are_exact():
    s = make_series(100)
    f = F.build_features(s)
    day = f.index[10]
    assert f.at[day, "lag_1"] == s.shift(1)[day] and f.at[day, "lag_7"] == s.shift(7)[day]
    assert f.at[day, "roll_mean_7"] == pytest.approx(s[:day].iloc[-8:-1].mean())      # the 7 days BEFORE the day


def test_next_row_features_match_training_features():
    """The row used for forecasting must be built exactly like a training row."""
    s = make_series(120)
    nxt = F.next_row_features(s.iloc[:-1])
    train_row = F.build_features(s).iloc[-1][F.FEATURES]
    assert np.allclose(nxt.iloc[0].to_numpy(dtype=float), train_row.to_numpy(dtype=float))


def test_ratio_model_predicts_price_from_percent_change():
    from sklearn.linear_model import LinearRegression
    s = make_series(200)
    f = F.build_features(s)
    m = F.RatioModel(LinearRegression()).fit(f[F.FEATURES].to_numpy(), f["target"].to_numpy())
    pred = m.predict(f[F.FEATURES].to_numpy()[-5:])
    assert np.all(np.abs(pred / f["target"].to_numpy()[-5:] - 1) < 0.05)


def test_recursive_forecast_length_and_dates():
    from sklearn.linear_model import LinearRegression
    s = make_series(200)
    f = F.build_features(s)
    m = F.RatioModel(LinearRegression()).fit(f[F.FEATURES].to_numpy(), f["target"].to_numpy())
    p = F.recursive_forecast(m, s, 7)
    assert len(p) == 7 and p.index[0] == s.index[-1] + pd.Timedelta(days=1)
    batch = F.recursive_forecast_batch(m, [s, s.iloc[:-10]], 7)
    assert batch.shape == (2, 7) and np.allclose(batch[0], p.to_numpy())


# ---------------------------------------------------------------- metrics + evaluation
def test_mape_rmse_known_values():
    assert T.mape([100, 200], [110, 180]) == pytest.approx(10.0)
    assert T.rmse([1, 2, 3], [1, 2, 6]) == pytest.approx(np.sqrt(3))


def test_evaluation_is_chronological_and_leak_free():
    ev = T.evaluate_commodity(make_series(260))
    assert set(ev["metrics"]) == set(T.MODEL_NAMES)
    assert ev["n_origins"] >= 8
    for name, m in ev["metrics"].items():
        assert 0 <= m["mape"] < 50 and m["rmse"] > 0
    # a flat series is trivially predictable: every sensible model must be very accurate
    flat = pd.Series(50.0, index=make_series(200).index)
    flat_ev = T.evaluate_commodity(flat * (1 + np.random.default_rng(1).normal(0, 0.001, 200)))
    assert flat_ev["metrics"]["naive"]["mape"] < 1


def test_training_skips_short_series(db, add_reference):
    add_reference("Rice", 40.0, days=60)
    r = T.train_commodity(db, "Rice", verbose=False)
    assert "skipped" in r


def test_training_selects_best_saves_model_and_metrics(db, isolated_models):
    from app.models import ReferencePrice
    s = make_series(240)
    for d, p in s.items():
        db.add(ReferencePrice(commodity="Rice", market="All India", price_date=d.date(), wholesale_price=float(p), retail_price=float(p) * 1.1, unit="kg", source="t"))
    db.commit()
    r = T.train_commodity(db, "Rice", verbose=False)
    assert r["best"] in T.MODEL_NAMES
    rows = db.query(ModelMetric).filter_by(commodity="Rice").all()
    assert len(rows) == 5 and sum(1 for m in rows if m.is_best) == 1
    best = [m for m in rows if m.is_best][0]
    assert best.mape == min(m.mape for m in rows)                       # the winner really has the lowest MAPE
    bundle = joblib.load(isolated_models / "Rice.joblib")
    assert bundle["modelName"] == r["best"] and bundle["residualStd"] > 0 and bundle["features"] == F.FEATURES
    assert not list(isolated_models.glob("*.tmp"))                      # atomic save left no temp file behind
    T.train_commodity(db, "Rice", verbose=False)                        # retraining replaces rows, never duplicates
    assert db.query(ModelMetric).filter_by(commodity="Rice").count() == 5


# ---------------------------------------------------------------- forecast service
def _trained(db, isolated_models, commodity="Rice", n=240):
    from app.models import ReferencePrice
    for d, p in make_series(n).items():
        db.add(ReferencePrice(commodity=commodity, market="All India", price_date=d.date(), wholesale_price=float(p), retail_price=float(p) * 1.1, unit="kg", source="t"))
    db.commit()
    T.train_commodity(db, commodity, verbose=False)


def test_forecast_structure_and_band(db, isolated_models):
    _trained(db, isolated_models)
    r = FS.forecast_for_commodity(db, "Rice", 14)
    assert len(r["forecast"]) == 14 and len(r["history"]) == 90
    first, last = r["forecast"][0], r["forecast"][-1]
    assert first["low"] <= first["price"] <= first["high"]
    assert (last["high"] - last["low"]) > (first["high"] - first["low"])      # uncertainty grows with the horizon
    assert r["direction"] in ("Rising", "Falling", "Stable") and r["mape"] is not None
    assert dt.date.fromisoformat(first["date"]) == dt.date.fromisoformat(r["latestDate"]) + dt.timedelta(days=1)


@pytest.mark.parametrize("change, direction", [(3.0, "Rising"), (2.99, "Stable"), (0, "Stable"), (-2.99, "Stable"), (-3.0, "Falling"), (-10, "Falling")])
def test_direction_thresholds(change, direction):
    assert FS.direction_of(change) == direction


def test_missing_and_corrupt_model(db, isolated_models):
    with pytest.raises(FS.NoModelError):
        FS.load_model("Nothing")
    isolated_models.mkdir(parents=True, exist_ok=True)
    (isolated_models / "Bad.joblib").write_bytes(b"not a model")
    with pytest.raises(FS.NoModelError):
        FS.load_model("Bad")


# ---------------------------------------------------------------- API
def test_api_unlinked_product(client, register_user, create_shop, create_product):
    h = register_user()
    create_shop(h)
    p = create_product(h, "Soap")
    r = client.get(f"/api/forecast/{p['id']}", headers=h).json()
    assert r["available"] is False and "not linked" in r["reason"]


def test_api_no_model_yet(client, shop_with_data):
    r = client.get(f"/api/forecast/{shop_with_data['product']['id']}", headers=shop_with_data["headers"]).json()
    assert r["available"] is False and "Retrain" in r["reason"]


def test_api_forecast_ok_and_horizon_validation(client, db, isolated_models, register_user, create_shop, create_product):
    _trained(db, isolated_models)
    h = register_user("f@test.com")
    create_shop(h)
    p = create_product(h, "Rice", referenceCommodity="Rice")
    r = client.get(f"/api/forecast/{p['id']}?horizon=14", headers=h).json()
    assert r["available"] is True and len(r["forecast"]) == 14 and r["productName"] == "Rice"
    assert client.get(f"/api/forecast/{p['id']}?horizon=9", headers=h).status_code == 422
    assert client.get("/api/forecast/models?commodity=Rice", headers=h).json()[0]["commodity"] == "Rice"
    assert len(client.get("/api/forecast/models", headers=h).json()) == 5


def test_api_forecast_other_shop_404(client, db, isolated_models, shop_with_data, register_user, create_shop):
    h2 = register_user("o@test.com")
    create_shop(h2)
    assert client.get(f"/api/forecast/{shop_with_data['product']['id']}", headers=h2).status_code == 404
    assert client.get("/api/forecast/1").status_code == 401


def test_retrain_job_states(client, register_user):
    from app.routers import forecast as fr
    h = register_user()
    fr._job.update(state="idle", message=None)
    assert client.post("/api/forecast/retrain?commodity=Nope", headers=h).status_code == 404
    fr._job.update(state="running")
    assert client.post("/api/forecast/retrain", headers=h).status_code == 409          # only one job at a time
    assert client.get("/api/forecast/retrain/status", headers=h).json()["state"] == "running"
    fr._job.update(state="idle")
