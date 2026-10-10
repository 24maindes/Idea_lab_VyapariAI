"""
ml/anomaly.py - price anomaly detection. Pure functions on pandas DataFrames (no database access).

IDEA: a purchase is "abnormal" when its price is far from what is normal for that product.
We look at it from three angles and let them vote:
  1. Z-score             how many standard deviations away from the product's own recent prices?
  2. Isolation Forest    a machine-learning model that isolates rare, odd-looking points quickly
  3. Threshold rule      simply: more than X % away from the market (reference) price
A purchase is flagged when 2 of the 3 agree, OR when it is more than 25 % off the market (so very
clear cases are never missed). Voting reduces false alarms because each method alone makes mistakes.

Input DataFrame columns: purchase_id, product_id, purchase_date, unit_price, reference_price (NaN if unknown)
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.services.config import (ANOMALY_CONTAMINATION, ANOMALY_HIGH_PCT, ANOMALY_IF_PER_PRODUCT_ROWS,
                                 ANOMALY_MEDIUM_PCT, ANOMALY_MIN_HISTORY, ANOMALY_STRONG_PCT, ANOMALY_Z_WINDOW_DAYS)

IF_COLUMNS = ["ratio_to_reference", "pct_change_prev", "zscore_90d"]
METHOD_LABELS = {"zscore": "Z-score", "isolation_forest": "Isolation Forest", "threshold": "Threshold rule"}


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds the columns the detectors need. Every feature only uses EARLIER purchases of the same product
    (never the future), so a live check of a new purchase gives the same answer as a later scan.
    """
    df = df.copy()
    df["purchase_date"] = pd.to_datetime(df["purchase_date"])
    df = df.sort_values(["product_id", "purchase_date", "purchase_id"]).reset_index(drop=True)

    # how far is the price from the market price? (1.0 = same as market)
    ref = df["reference_price"].where(df["reference_price"] > 0)
    df["ratio_to_reference"] = (df["unit_price"] / ref).fillna(1.0)

    # change versus the previous purchase of the same product, in %
    df["pct_change_prev"] = (df.groupby("product_id")["unit_price"].pct_change() * 100).fillna(0.0)

    z = np.zeros(len(df))
    med_dev = np.zeros(len(df))
    for _, idx in df.groupby("product_id").indices.items():
        prices = df["unit_price"].to_numpy()[idx]
        dates = df["purchase_date"].to_numpy()[idx]
        for k in range(len(idx)):
            earlier = prices[:k]
            # z-score against earlier purchases of the last 90 days
            in_window = earlier[dates[:k] >= dates[k] - np.timedelta64(ANOMALY_Z_WINDOW_DAYS, "D")]
            if len(in_window) >= ANOMALY_MIN_HISTORY and in_window.std() > 0:
                z[idx[k]] = (prices[k] - in_window.mean()) / in_window.std()
            # % away from the median of the last 5 purchases (a robust "recent normal price")
            recent = earlier[-5:]
            if len(recent) >= 3:
                med_dev[idx[k]] = (prices[k] / np.median(recent) - 1) * 100
    df["zscore_90d"] = z
    df["rolling_median_dev"] = med_dev

    # deviation used for thresholds and messages: versus the market when we know it, else versus recent purchases
    has_ref = df["reference_price"] > 0
    df["deviation_pct"] = np.where(has_ref, (df["ratio_to_reference"] - 1) * 100, df["rolling_median_dev"])
    return df


def zscore_flags(features: pd.DataFrame, cutoff: float = 2.5) -> pd.DataFrame:
    """Flag purchases whose z-score is beyond +/- cutoff (2.5 = about 1 in 80 normal prices)."""
    score = features["zscore_90d"].abs()
    return pd.DataFrame({"flag": score > cutoff, "score": score}, index=features.index)


def threshold_flags(features: pd.DataFrame, threshold_pct: float = 15) -> pd.DataFrame:
    """Flag purchases more than threshold_pct away from the market price (or recent normal if no market price)."""
    score = features["deviation_pct"].abs()
    return pd.DataFrame({"flag": score > threshold_pct, "score": score}, index=features.index)


def isolation_forest_flags(features: pd.DataFrame, contamination: float = ANOMALY_CONTAMINATION,
                           random_state: int = 42) -> pd.DataFrame:
    """
    Isolation Forest: builds random trees that split the data; odd points get isolated after very few splits.
    One model per product when it has 30+ purchases (each product has its own normal), otherwise one model on all rows.
    Features are standardised first so no column dominates. Needs at least 10 rows to say anything.
    """
    flag = pd.Series(False, index=features.index)
    score = pd.Series(0.0, index=features.index)

    def fit_group(sub: pd.DataFrame) -> None:
        if len(sub) < 10:
            return
        X = StandardScaler().fit_transform(sub[IF_COLUMNS].to_numpy())
        model = IsolationForest(n_estimators=100, contamination=min(contamination, 0.5), random_state=random_state).fit(X)
        flag.loc[sub.index] = model.predict(X) == -1
        score.loc[sub.index] = -model.score_samples(X)         # higher = more unusual

    counts = features.groupby("product_id")["purchase_id"].transform("count")
    big = features[counts >= ANOMALY_IF_PER_PRODUCT_ROWS]
    small = features[counts < ANOMALY_IF_PER_PRODUCT_ROWS]
    for _, sub in big.groupby("product_id"):
        fit_group(sub)
    if len(small):
        fit_group(small)
    return pd.DataFrame({"flag": flag, "score": score})


def ensemble(features: pd.DataFrame, cutoff: float = 2.5, threshold_pct: float = 15,
             contamination: float = ANOMALY_CONTAMINATION, if_flags: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Combine the three detectors. Output per row: flagged, methods (list), severity, score (0-1),
    deviationPct, direction ('above' / 'below' market).
    """
    z = zscore_flags(features, cutoff)
    t = threshold_flags(features, threshold_pct)
    f = if_flags if if_flags is not None else isolation_forest_flags(features, contamination)   # if_flags: reuse (grid search)

    votes = z["flag"].astype(int) + t["flag"].astype(int) + f["flag"].astype(int)
    dev = features["deviation_pct"]
    strong = dev.abs() > ANOMALY_STRONG_PCT
    flagged = (votes >= 2) | strong

    methods = []
    for i in features.index:
        m = []
        if z.at[i, "flag"]:
            m.append("zscore")
        if f.at[i, "flag"]:
            m.append("isolation_forest")
        if t.at[i, "flag"]:
            m.append("threshold")
        methods.append(m)

    severity = np.where((dev.abs() > ANOMALY_HIGH_PCT) | (votes == 3), "high",
                        np.where((dev.abs() > ANOMALY_MEDIUM_PCT) | (votes == 2), "medium", "low"))
    score = (votes / 3 * 0.6 + np.minimum(dev.abs() / 50, 1) * 0.4).round(3)

    out = pd.DataFrame({
        "purchase_id": features["purchase_id"], "flagged": flagged, "methods": methods, "severity": severity,
        "score": score, "deviationPct": dev.round(1),
        "direction": np.where(dev >= 0, "above", "below"),
        "votes": votes,
    }, index=features.index)
    out.loc[~out["flagged"], "severity"] = "none"
    return out
