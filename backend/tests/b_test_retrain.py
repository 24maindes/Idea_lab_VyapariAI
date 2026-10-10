"""Retraining is safe: it never leaves the app without a model, and failures are reported, not thrown."""
import joblib
import numpy as np
import pandas as pd
import pytest

from app.ml import train_forecast as T
from app.models import ModelMetric, ReferencePrice
from app.routers import forecast as fr
from app.services import forecast_service as FS
from conftest import TODAY


def fill(db, commodity="Rice", days=240, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(end=pd.Timestamp(TODAY), periods=days, freq="D")
    for d, p in zip(idx, 40 * np.exp(rng.normal(0, 0.004, days)).cumprod() ** 0.3):
        db.add(ReferencePrice(commodity=commodity, market="All India", price_date=d.date(), wholesale_price=float(p), retail_price=float(p) * 1.1, unit="kg", source="t"))
    db.commit()


def test_failed_training_keeps_the_old_model_and_old_metrics(db, isolated_models, monkeypatch):
    fill(db)
    assert "best" in T.train_commodity(db, "Rice", verbose=False)
    path = isolated_models / "Rice.joblib"
    before = path.read_bytes()
    metrics_before = sorted((m.model_name, m.mape) for m in db.query(ModelMetric).all())

    monkeypatch.setattr(T, "fit_final", lambda *a, **k: (_ for _ in ()).throw(ValueError("boom")))
    r = T.train_commodity(db, "Rice", verbose=False)
    assert "error" in r and "boom" in r["error"]
    assert path.read_bytes() == before                                              # the old model file is untouched
    assert sorted((m.model_name, m.mape) for m in db.query(ModelMetric).all()) == metrics_before
    assert not list(isolated_models.glob("*.tmp")) and joblib.load(path)["modelName"]


def test_crash_while_writing_leaves_no_partial_file(db, isolated_models, monkeypatch):
    fill(db)
    T.train_commodity(db, "Rice", verbose=False)
    good = (isolated_models / "Rice.joblib").read_bytes()
    monkeypatch.setattr(T.joblib, "dump", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    assert "error" in T.train_commodity(db, "Rice", verbose=False)
    assert (isolated_models / "Rice.joblib").read_bytes() == good and not list(isolated_models.glob("*.tmp"))


def test_short_series_is_skipped_with_a_reason(db, isolated_models):
    fill(db, "Short", days=100)
    r = T.train_commodity(db, "Short", verbose=False)
    assert r == {"commodity": "Short", "skipped": "only 100 days of data (need 120)"} and not isolated_models.exists() or not list(isolated_models.glob("Short*"))


def _use_test_db(monkeypatch, db):
    """The training script opens its own session; point it at the test database instead."""
    monkeypatch.setattr(T, "SessionLocal", lambda: db)
    monkeypatch.setattr(T, "engine", db.get_bind())
    monkeypatch.setattr(db, "close", lambda: None)


def test_one_failing_commodity_does_not_stop_the_others(db, isolated_models, monkeypatch):
    fill(db, "Rice")
    fill(db, "Sugar", seed=5)
    _use_test_db(monkeypatch, db)
    real = T.fit_final

    def flaky(name, series):
        if series.name == "Sugar":
            raise RuntimeError("bad data")
        return real(name, series)
    monkeypatch.setattr(T, "fit_final", flaky)
    results = {r["commodity"]: r for r in T.main(None, verbose=False)}
    assert "best" in results["Rice"] and "bad data" in results["Sugar"]["error"]
    assert (isolated_models / "Rice.joblib").exists() and not (isolated_models / "Sugar.joblib").exists()


def test_retrain_job_reports_structured_results(client, register_user, db, isolated_models, monkeypatch):
    fill(db, "Rice")
    fill(db, "Tiny", days=50)
    _use_test_db(monkeypatch, db)
    h = register_user()
    fr._job.update(state="idle", message=None)
    r = client.post("/api/forecast/retrain", headers=h)
    assert r.status_code == 202 and r.json()["state"] == "running"
    s = client.get("/api/forecast/retrain/status", headers=h).json()                  # the background task already ran
    assert s["state"] == "done" and s["trained"] == 1 and s["skipped"] == [{"commodity": "Tiny", "reason": "only 50 days of data (need 120)"}] and s["failed"] == []
    assert "Trained 1 commodity" in s["message"] and (isolated_models / "Rice.joblib").exists()


def test_retrain_with_nothing_trainable_is_an_error_state(client, register_user, db, isolated_models, monkeypatch):
    fill(db, "Tiny", days=50)
    _use_test_db(monkeypatch, db)
    h = register_user()
    fr._job.update(state="idle")
    client.post("/api/forecast/retrain", headers=h)
    s = client.get("/api/forecast/retrain/status", headers=h).json()
    assert s["state"] == "error" and s["message"].startswith("Nothing was trained") and s["trained"] == 0


def test_forecast_cache_is_cleared_after_retraining(db, isolated_models):
    fill(db)
    T.train_commodity(db, "Rice", verbose=False)
    first = FS.forecast_for_commodity(db, "Rice", 7)
    assert FS.forecast_for_commodity(db, "Rice", 7) is first                           # cached object
    FS.invalidate_forecasts("Rice")
    assert FS.forecast_for_commodity(db, "Rice", 7) is not first


def test_new_model_file_is_picked_up_by_its_modified_time(db, isolated_models):
    fill(db)
    T.train_commodity(db, "Rice", verbose=False)
    b1 = FS.load_model("Rice")
    T.train_commodity(db, "Rice", verbose=False)                                       # rewrites the file
    assert FS.load_model("Rice") is not b1
