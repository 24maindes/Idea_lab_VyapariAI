"""
train_forecast.py - train, compare and save the price forecasting models.

    python -m app.ml.train_forecast                  # all commodities
    python -m app.ml.train_forecast --commodity Rice

WHAT HAPPENS FOR EACH COMMODITY
1. Load the daily price series and build features (only past information, see features.py).
2. CHRONOLOGICAL split: the last max(60 days, 20 %) is the TEST period. We never shuffle time series,
   because shuffling would let the model "see the future".
3. Five contenders:
     naive        tomorrow = today (the bar every real model must beat)
     linear       LinearRegression, a simple baseline on the lag features
     rf           RandomForest, 300 trees: many small trees averaged = stable on small noisy tables
     xgb          XGBoost, 400 shallow trees (depth 4), learning rate 0.05 = slow careful learning, hard to overfit
     holt_winters Holt-Winters exponential smoothing: classic time-series method (trend + weekly pattern)
4. ROLLING-ORIGIN EVALUATION: every 7 days inside the test period we pretend "today is origin day",
   train only on data up to that day, and forecast the NEXT 7 days. We compare with what really happened
   and average the errors over all origins. This mimics real use (forecast a week ahead, again and again).
   - ML models forecast recursively (each predicted day becomes input for the next day).
   - Holt-Winters forecasts 7 steps directly.
   - The model is trained ONCE on the data before the test period and reused for all origins (fast);
     only the history it looks at moves forward. That is still leak-free.
5. Metrics: MAPE (average % error, easy to explain to a shopkeeper) and RMSE (in rupees, punishes big misses).
6. The model with the lowest MAPE wins, is refitted on ALL data and saved to models_store/{commodity}.joblib
   together with the residual standard deviation (used for the confidence band).
"""
import argparse
import datetime as dt
import os
import tempfile
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sqlalchemy import delete
from xgboost import XGBRegressor

from app.database import Base, SessionLocal, engine
from app.ml.features import (FEATURES, MIN_HISTORY, RatioModel, build_features, load_series, recursive_forecast,
                             recursive_forecast_batch)
from app.models import ModelMetric, ReferencePrice

warnings.filterwarnings("ignore")

BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BACKEND_DIR / "models_store"
EVAL_DIR = BACKEND_DIR.parent / "docs" / "eval"
HORIZON = 7
MIN_SERIES_DAYS = 120          # shorter series are skipped (not enough history for lag features + a test period)
MODEL_NAMES = ["naive", "linear", "rf", "xgb", "holt_winters"]


class NaiveModel:
    """Predicts that the price stays the same as the last known price."""
    def fit(self, X, y):
        return self


def make_model(name: str):
    # all three learn the % change from yesterday (see RatioModel), then convert back to a price
    if name == "linear":
        return RatioModel(LinearRegression())
    if name == "rf":
        # 300 trees, min_samples_leaf=3: averaging many trees smooths noise; the leaf limit stops single-day quirks being memorised.
        # n_jobs=1: we call predict thousands of times on ONE row, thread start-up would cost more than it saves.
        return RatioModel(RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=42, n_jobs=1))
    if name == "xgb":
        # small learning rate + shallow trees + many rounds = gradual learning, little overfitting on ~2000 rows
        return RatioModel(XGBRegressor(n_estimators=400, learning_rate=0.05, max_depth=4, subsample=0.9, random_state=42, n_jobs=1, verbosity=0))
    return NaiveModel()


def holt_winters_forecast(history: pd.Series, steps: int) -> np.ndarray:
    """Holt-Winters: additive trend + additive weekly seasonality when there is enough data (else trend only)."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    recent = history.iloc[-150:]                                  # ~5 months is plenty for a weekly pattern and keeps it fast
    seasonal = "add" if len(recent) >= 28 else None
    try:
        fit = ExponentialSmoothing(recent.to_numpy(), trend="add", damped_trend=True, seasonal=seasonal,
                                   seasonal_periods=7 if seasonal else None).fit()
        return np.asarray(fit.forecast(steps))
    except Exception:
        return np.repeat(recent.iloc[-1], steps)                  # never crash: fall back to naive


def predict_path(name: str, model, history: pd.Series, steps: int) -> np.ndarray:
    if name == "naive":
        return np.repeat(history.iloc[-1], steps)
    if name == "holt_winters":
        return holt_winters_forecast(history, steps)
    return recursive_forecast(model, history, steps).to_numpy()


def mape(actual, pred) -> float:
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    return float(np.mean(np.abs((actual - pred) / actual)) * 100)


def rmse(actual, pred) -> float:
    return float(np.sqrt(np.mean((np.asarray(actual, float) - np.asarray(pred, float)) ** 2)))


def evaluate_commodity(series: pd.Series) -> dict:
    """Returns {'metrics': {name: {'mape','rmse'}}, 'residual_std': {name: sd}, 'test_start': date, 'test_preds': ...}"""
    feats = build_features(series)
    n_test = max(60, int(len(series) * 0.2))
    test_start = series.index[-n_test]
    train = feats[feats.index < test_start]

    models = {}
    for name in MODEL_NAMES:
        m = make_model(name)
        if name in ("linear", "rf", "xgb"):
            m.fit(train[FEATURES].to_numpy(), train["target"].to_numpy())
        models[name] = m

    test_days = series.index[series.index >= test_start]
    origins = [test_days[i] for i in range(0, len(test_days) - HORIZON + 1, HORIZON)]   # one origin per week
    origins = [o for o in origins if len(series[series.index < o]) >= MIN_HISTORY and len(series[series.index >= o]) >= HORIZON]
    histories = [series[series.index < o] for o in origins]               # only what was known BEFORE each origin day
    actuals = [series[series.index >= o].iloc[:HORIZON].to_numpy() for o in origins]

    errs = {n: {"mape": [], "rmse": [], "one_step": []} for n in MODEL_NAMES}
    best_path_store = {n: [] for n in MODEL_NAMES}
    for n in MODEL_NAMES:
        if n in ("linear", "rf", "xgb"):
            paths = recursive_forecast_batch(models[n], histories, HORIZON)      # all origins at once
        else:
            paths = np.array([predict_path(n, models[n], h, HORIZON) for h in histories])
        for o, actual, path in zip(origins, actuals, paths):
            errs[n]["mape"].append(mape(actual, path))
            errs[n]["rmse"].append(rmse(actual, path))
            errs[n]["one_step"].append(actual[0] - path[0])
            best_path_store[n].append((o, actual, path))

    metrics = {n: {"mape": float(np.mean(e["mape"])), "rmse": float(np.mean(e["rmse"]))} for n, e in errs.items() if e["mape"]}
    resid_std = {n: float(np.std(e["one_step"])) for n, e in errs.items() if e["one_step"]}
    return {"metrics": metrics, "residual_std": resid_std, "test_start": test_start, "paths": best_path_store, "n_origins": len(origins)}


def fit_final(name: str, series: pd.Series):
    """Refit the winning model on ALL data."""
    m = make_model(name)
    if name in ("linear", "rf", "xgb"):
        feats = build_features(series)
        m.fit(feats[FEATURES].to_numpy(), feats["target"].to_numpy())
    return m


def save_model_atomically(commodity: str, bundle: dict) -> Path:
    """Write to a temp file first, then replace the old file in one step, so a crash never leaves a broken model."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    final = MODEL_DIR / f"{commodity}.joblib"
    fd, tmp = tempfile.mkstemp(dir=MODEL_DIR, suffix=".tmp")
    os.close(fd)
    try:
        joblib.dump(bundle, tmp)
        os.replace(tmp, final)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return final


def train_commodity(db, commodity: str, verbose: bool = True) -> dict:
    """
    Train, evaluate, select, save, store metrics. Returns a result dict:
      {'commodity', 'best', 'metrics', ...}   success
      {'commodity', 'skipped': reason}         not enough data (no model is touched)
      {'commodity', 'error': message}          something failed; the OLD model file and old metrics stay exactly as they were
    The old .joblib is replaced only AFTER the new one was fully written (atomic os.replace), so the app is never left without a model.
    """
    series = load_series(db, commodity)
    if len(series) < MIN_SERIES_DAYS:
        msg = f"only {len(series)} days of data (need {MIN_SERIES_DAYS})"
        if verbose:
            print(f"[skip] {commodity}: {msg}")
        return {"commodity": commodity, "skipped": msg}

    try:
        ev = evaluate_commodity(series)
        metrics = ev["metrics"]
        best = min(metrics, key=lambda n: metrics[n]["mape"])
        model = fit_final(best, series)
        # naive / holt_winters have nothing to pickle (Holt-Winters is refitted at forecast time); storing None also
        # avoids pickling a class that lives in __main__ when the script is run with python -m
        bundle = {"model": model if best in ("linear", "rf", "xgb") else None, "modelName": best, "features": FEATURES,
                  "lastDate": series.index[-1].date().isoformat(),
                  "residualStd": ev["residual_std"].get(best, float(series.iloc[-30:].std())), "horizonDays": HORIZON}
        save_model_atomically(commodity, bundle)                 # 1. model file first (atomic) ...

        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)   # 2. ... then the metric rows, in one transaction
        db.execute(delete(ModelMetric).where(ModelMetric.commodity == commodity))
        for n, m in metrics.items():
            db.add(ModelMetric(commodity=commodity, model_name=n, mape=round(m["mape"], 3), rmse=round(m["rmse"], 3),
                               is_best=(n == best), horizon_days=HORIZON, trained_at=now))
        db.commit()
    except Exception as e:
        db.rollback()
        if verbose:
            print(f"[error] {commodity}: {type(e).__name__}: {e}")
        return {"commodity": commodity, "error": f"{type(e).__name__}: {e}"}

    if verbose:
        print(f"\n{commodity}  ({len(series)} days, test from {ev['test_start'].date()}, {ev['n_origins']} weekly origins)")
        print(f"  {'model':<14}{'MAPE %':>9}{'RMSE Rs':>10}")
        for n in sorted(metrics, key=lambda k: metrics[k]["mape"]):
            print(f"  {n:<14}{metrics[n]['mape']:>9.2f}{metrics[n]['rmse']:>10.2f}{'   <- best' if n == best else ''}")
    return {"commodity": commodity, "best": best, "metrics": metrics, "ev": ev, "series": series}


def main(commodity: str | None = None, verbose: bool = True) -> list[dict]:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        names = [commodity] if commodity else [r[0] for r in db.query(ReferencePrice.commodity).distinct().order_by(ReferencePrice.commodity)]
        if not names:
            raise SystemExit("reference_prices is empty. Run build_reference and load_reference first.")
        results = [train_commodity(db, c, verbose) for c in names]
    finally:
        db.close()

    rows = [{"commodity": r["commodity"], "model": n, "mape": round(m["mape"], 3), "rmse": round(m["rmse"], 3), "is_best": n == r["best"]}
            for r in results if "metrics" in r for n, m in r["metrics"].items()]
    if rows and not commodity:                                    # only a full run rewrites the CSV
        EVAL_DIR.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(EVAL_DIR / "forecast_metrics.csv", index=False)
        if verbose:
            print(f"\nSaved {EVAL_DIR / 'forecast_metrics.csv'}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--commodity", default=None)
    main(ap.parse_args().commodity)
