"""
services/forecast_service.py - load a trained model and produce a price forecast for one commodity.
"""
import threading
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.features import load_series, recursive_forecast
from app.ml.train_forecast import MODEL_DIR, holt_winters_forecast
from app.models import ModelMetric
from app.services.config import (FORECAST_BAND_Z, FORECAST_FALLING_PCT, FORECAST_HISTORY_DAYS,
                                 FORECAST_RISING_PCT)

FORECAST_CACHE_SECONDS = 600


class NoModelError(Exception):
    """No trained model exists for this commodity (or it could not be loaded)."""


_model_cache: dict[str, tuple[float, dict]] = {}      # commodity -> (file modified time, bundle)
_forecast_cache: dict[tuple, tuple[float, dict]] = {}
_lock = threading.Lock()


def model_path(commodity: str) -> Path:
    return MODEL_DIR / f"{commodity}.joblib"


def load_model(commodity: str) -> dict:
    """Bundle {model, modelName, features, lastDate, residualStd, horizonDays}. Cached; reloaded if the file changes."""
    path = model_path(commodity)
    if not path.exists():
        raise NoModelError(f"No trained model for {commodity}")
    mtime = path.stat().st_mtime
    with _lock:
        hit = _model_cache.get(commodity)
        if hit and hit[0] == mtime:
            return hit[1]
    try:
        bundle = joblib.load(path)
    except Exception as e:                              # corrupt file, version mismatch ...
        raise NoModelError(f"Model file for {commodity} could not be loaded: {e}") from e
    with _lock:
        _model_cache[commodity] = (mtime, bundle)
    return bundle


def invalidate_forecasts(commodity: str | None = None) -> None:
    """Call after retraining so users immediately see forecasts from the new model."""
    with _lock:
        if commodity is None:
            _model_cache.clear()
            _forecast_cache.clear()
        else:
            _model_cache.pop(commodity, None)
            for k in [k for k in _forecast_cache if k[0] == commodity]:
                _forecast_cache.pop(k, None)


def direction_of(change_pct: float) -> str:
    if change_pct >= FORECAST_RISING_PCT:
        return "Rising"
    if change_pct <= FORECAST_FALLING_PCT:
        return "Falling"
    return "Stable"


def _predict(bundle: dict, series: pd.Series, horizon: int) -> np.ndarray:
    name = bundle["modelName"]
    if name == "naive":
        return np.repeat(series.iloc[-1], horizon)
    if name == "holt_winters":
        return holt_winters_forecast(series, horizon)
    return recursive_forecast(bundle["model"], series, horizon).to_numpy()


def forecast_for_commodity(db: Session, commodity: str, horizon: int = 7) -> dict:
    """
    {commodity, modelName, mape, rmse, latestPrice, latestDate, history: last 90 days,
     forecast: [{date, price, low, high}], changePct, direction}
    Confidence band = price +/- 1.28 x residualStd x sqrt(step): the further ahead, the wider (errors pile up).
    """
    bundle = load_model(commodity)
    series = load_series(db, commodity)
    if series.empty:
        raise NoModelError(f"No reference prices for {commodity}")

    key = (commodity, horizon, series.index[-1].date().isoformat())
    now = time.time()
    with _lock:
        hit = _forecast_cache.get(key)
        if hit and hit[0] > now:
            return hit[1]

    prices = _predict(bundle, series, horizon)
    days = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")
    std = float(bundle.get("residualStd") or 0.0)
    forecast = []
    for step, (d, p) in enumerate(zip(days, prices), start=1):
        half = FORECAST_BAND_Z * std * np.sqrt(step)
        forecast.append({"date": d.date().isoformat(), "price": round(float(p), 2),
                         "low": round(float(max(p - half, 0)), 2), "high": round(float(p + half), 2)})

    latest = float(series.iloc[-1])
    day7 = forecast[min(6, horizon - 1)]["price"]
    change_pct = round((day7 / latest - 1) * 100, 2) if latest else 0.0

    metric = db.execute(select(ModelMetric).where(ModelMetric.commodity == commodity, ModelMetric.is_best.is_(True))).scalars().first()
    result = {
        "commodity": commodity, "modelName": bundle["modelName"],
        "mape": metric.mape if metric else None, "rmse": metric.rmse if metric else None,
        "latestPrice": round(latest, 2), "latestDate": series.index[-1].date().isoformat(),
        "history": [{"date": d.date().isoformat(), "price": round(float(v), 2)} for d, v in series.iloc[-FORECAST_HISTORY_DAYS:].items()],
        "forecast": forecast, "changePct": change_pct, "direction": direction_of(change_pct),
    }
    with _lock:
        _forecast_cache[key] = (now + FORECAST_CACHE_SECONDS, result)
    return result


def warm_up() -> int:
    """Load every saved model into memory (the first forecast request is otherwise slow because XGBoost / scikit-learn load lazily)."""
    count = 0
    if MODEL_DIR.exists():
        for f in sorted(MODEL_DIR.glob("*.joblib")):
            try:
                load_model(f.stem)
                count += 1
            except NoModelError:
                pass
    return count
