"""
features.py - turn a daily price series into a table a model can learn from.

LEAKAGE PREVENTION (the most important rule, easy to explain in a viva):
every feature for day t is computed from days BEFORE t only. We do this by calling .shift(1)
BEFORE any rolling mean / std, so "roll_mean_7" at day t is the average of days t-7 ... t-1,
never including day t itself. The target (what we predict) is the price on day t.
"""
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ReferencePrice

FEATURES = ["lag_1", "lag_7", "lag_14", "lag_28", "roll_mean_7", "roll_mean_14", "roll_mean_30",
            "roll_std_7", "roll_std_14", "pct_change_7", "day_of_week", "month", "doy_sin", "doy_cos"]
MIN_HISTORY = 30   # days of history needed before the first usable row (largest window is 28-30)


def load_series(db: Session, commodity: str, kind: str = "wholesale") -> pd.Series:
    """Daily price series (index = date). Small gaps (up to 7 days) are filled by interpolation."""
    col = ReferencePrice.wholesale_price if kind == "wholesale" else ReferencePrice.retail_price
    rows = db.execute(select(ReferencePrice.price_date, col).where(ReferencePrice.commodity == commodity, col.is_not(None))
                      .order_by(ReferencePrice.price_date)).all()
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series([float(r[1]) for r in rows], index=pd.to_datetime([r[0] for r in rows]), name=commodity)
    s = s[~s.index.duplicated(keep="last")]
    return s.asfreq("D").interpolate(limit=7).dropna()


def _calendar(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Calendar features are known in advance (the date itself), so they cannot leak the future."""
    doy = index.dayofyear.to_numpy()
    return pd.DataFrame({
        "day_of_week": index.dayofweek.to_numpy(),
        "month": index.month.to_numpy(),
        "doy_sin": np.sin(2 * np.pi * doy / 365.25),     # sin/cos make day 365 and day 1 neighbours
        "doy_cos": np.cos(2 * np.pi * doy / 365.25),
    }, index=index)


def build_features(series: pd.Series) -> pd.DataFrame:
    """One row per day: the 14 FEATURES plus 'target' (that day's price). Rows without enough history are dropped."""
    past = series.shift(1)                                # everything below only sees yesterday and before
    df = pd.DataFrame(index=series.index)
    for lag in (1, 7, 14, 28):
        df[f"lag_{lag}"] = series.shift(lag)
    for w in (7, 14, 30):
        df[f"roll_mean_{w}"] = past.rolling(w).mean()
    for w in (7, 14):
        df[f"roll_std_{w}"] = past.rolling(w).std()
    df["pct_change_7"] = (past / series.shift(8) - 1) * 100       # change over the week ending yesterday
    df = df.join(_calendar(series.index))
    df["target"] = series
    return df.dropna()


def next_row_features(history: pd.Series) -> pd.DataFrame:
    """
    Features for the day AFTER the last day of `history` (used for recursive forecasting:
    we append our own prediction to the history and ask for the next row again).
    """
    next_day = history.index[-1] + pd.Timedelta(days=1)
    ext = pd.concat([history, pd.Series([np.nan], index=[next_day])])
    past = ext.shift(1)
    row = {}
    for lag in (1, 7, 14, 28):
        row[f"lag_{lag}"] = ext.shift(lag).iloc[-1]
    for w in (7, 14, 30):
        row[f"roll_mean_{w}"] = past.rolling(w).mean().iloc[-1]
    for w in (7, 14):
        row[f"roll_std_{w}"] = past.rolling(w).std().iloc[-1]
    row["pct_change_7"] = (past / ext.shift(8) - 1).iloc[-1] * 100
    cal = _calendar(pd.DatetimeIndex([next_day])).iloc[0].to_dict()
    row.update(cal)
    return pd.DataFrame([row], index=[next_day])[FEATURES]


def recursive_forecast(model, history: pd.Series, steps: int) -> pd.Series:
    """Predict `steps` days ahead one day at a time, feeding each prediction back as the newest 'price'."""
    hist = history.copy()
    preds = {}
    for _ in range(steps):
        x = next_row_features(hist)
        y = float(model.predict(x.to_numpy())[0])
        preds[x.index[0]] = y
        hist = pd.concat([hist, pd.Series([y], index=x.index)])
    return pd.Series(preds)


class RatioModel:
    """
    Wraps a regressor so it predicts the PERCENT CHANGE from yesterday's price instead of the price itself.
    Why: market prices drift upwards over the years. Tree models (Random Forest, XGBoost) can only output values
    they saw in training, so on a rising series they get stuck at old price levels. A percent change stays in a
    familiar range (e.g. -2 % ... +2 %), so the trees work, and we convert back with  price = yesterday x (1 + change).
    """
    def __init__(self, base):
        self.base = base

    def fit(self, X, y):
        lag1 = X[:, FEATURES.index("lag_1")]
        self.base.fit(X, y / lag1 - 1.0)
        return self

    def predict(self, X):
        lag1 = X[:, FEATURES.index("lag_1")]
        return lag1 * (1.0 + self.base.predict(X))


def recursive_forecast_batch(model, histories: list, steps: int) -> np.ndarray:
    """
    Same as recursive_forecast, but for MANY histories at once (one per evaluation origin).
    All origins advance one day together, so the model is called `steps` times instead of
    `steps x number_of_origins` times. Much faster, identical results.
    """
    hists = [h.copy() for h in histories]
    out = np.zeros((len(hists), steps))
    for k in range(steps):
        X = np.vstack([next_row_features(h).to_numpy() for h in hists])
        y = model.predict(X)
        out[:, k] = y
        hists = [pd.concat([h, pd.Series([float(v)], index=[h.index[-1] + pd.Timedelta(days=1)])]) for h, v in zip(hists, y)]
    return out
