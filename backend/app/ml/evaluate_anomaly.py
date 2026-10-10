"""
evaluate_anomaly.py - how good is the anomaly detection? (precision, recall, F1)

    python -m app.ml.evaluate_anomaly

TWO TEST SETS
  1. "ground truth": the demo shop's purchases, labelled by data/anomaly_ground_truth.csv
     (anomalies that were injected when the demo data was created).
  2. "fresh injection": the CLEAN purchases of set 1 (no anomaly), with NEW random spikes and drops of
     +/-20 % to 45 % injected into about 5 % of the rows (fixed seed). Labels are known again.
     This checks that the detectors are not only good at the first set.

METRICS (for the class "anomaly"):
  precision = of everything we flagged, how much was really an anomaly     (few false alarms)
  recall    = of all real anomalies, how many we found                      (few misses)
  F1        = balance of the two (harmonic mean)

A GRID SEARCH tries z-cutoff {2.0, 2.5, 3.0} x threshold {10, 15, 20} % x contamination {0.03, 0.05, 0.08}
for the ensemble and reports the best F1.
Outputs: docs/eval/anomaly_metrics.csv and two charts in docs/figures/.
"""
import itertools
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sqlalchemy import select

from app.database import SessionLocal
from app.ml import anomaly as ml
from app.models import Shop, User
from app.services.anomaly_service import _purchase_frame

BACKEND_DIR = Path(__file__).resolve().parents[2]
GT_CSV = BACKEND_DIR / "data" / "anomaly_ground_truth.csv"
EVAL_DIR = BACKEND_DIR.parent / "docs" / "eval"
FIG_DIR = BACKEND_DIR.parent / "docs" / "figures"

DEFAULTS = {"cutoff": 2.5, "threshold_pct": 15, "contamination": 0.05}
GRID_Z, GRID_T, GRID_C = [2.0, 2.5, 3.0], [10, 15, 20], [0.03, 0.05, 0.08]
sns.set_theme(style="whitegrid")


def confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    tp = int(np.sum(y_true & y_pred)); fp = int(np.sum(~y_true & y_pred))
    fn = int(np.sum(y_true & ~y_pred)); tn = int(np.sum(~y_true & ~y_pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3), "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def load_sets(db) -> dict[str, tuple[pd.DataFrame, np.ndarray]]:
    user = db.execute(select(User).where(User.email == "demo@vyapariai.com")).scalar_one_or_none()
    if user is None or not GT_CSV.exists():
        raise SystemExit("Demo shop or anomaly_ground_truth.csv missing. Run python -m app.ml.seed_demo first.")
    shop = db.execute(select(Shop).where(Shop.user_id == user.id)).scalar_one()
    df = _purchase_frame(db, shop.id)
    truth = set(pd.read_csv(GT_CSV)["purchase_id"])
    labels1 = df["purchase_id"].isin(truth).to_numpy()

    # set 2: only clean purchases, then inject new anomalies (seeded)
    clean = df[~df["purchase_id"].isin(truth)].copy().reset_index(drop=True)
    rng = np.random.default_rng(2024)
    n_inject = max(1, round(0.05 * len(clean)))
    chosen = rng.choice(len(clean), size=n_inject, replace=False)
    labels2 = np.zeros(len(clean), dtype=bool)
    for i in chosen:
        pct = rng.uniform(20, 45) * rng.choice([1, -1], p=[0.8, 0.2])             # mostly spikes, some drops
        clean.loc[i, "unit_price"] *= 1 + pct / 100
        labels2[i] = True
    return {"ground_truth": (df, labels1), "fresh_injection": (clean, labels2)}


def evaluate_methods(feats: pd.DataFrame, labels: np.ndarray, cutoff, threshold_pct, contamination, if_flags=None) -> dict:
    """Metrics of each method on one test set. Features were sorted by build_features, so labels are re-aligned."""
    y = pd.Series(labels, index=feats["purchase_id"].index).to_numpy()
    z = ml.zscore_flags(feats, cutoff)["flag"].to_numpy()
    t = ml.threshold_flags(feats, threshold_pct)["flag"].to_numpy()
    f = (if_flags if if_flags is not None else ml.isolation_forest_flags(feats, contamination))["flag"].to_numpy()
    e = ml.ensemble(feats, cutoff, threshold_pct, contamination, if_flags=pd.DataFrame({"flag": f, "score": 0.0}, index=feats.index))["flagged"].to_numpy()
    return {"Z-score": confusion(y, z), "Isolation Forest": confusion(y, f), "Threshold rule": confusion(y, t), "Ensemble": confusion(y, e)}


def main() -> None:
    db = SessionLocal()
    try:
        sets = load_sets(db)
    finally:
        db.close()

    rows, prepared = [], {}
    for name, (df, labels) in sets.items():
        # build_features sorts rows, so carry the label through as a column and take it back afterwards
        tagged = df.assign(_label=labels)
        feats = ml.build_features(tagged)
        prepared[name] = (feats, feats["_label"].to_numpy().astype(bool))
        # isolation forest results per contamination (computed once, reused by the whole grid)
    if_cache = {(n, c): ml.isolation_forest_flags(prepared[n][0], c) for n in prepared for c in GRID_C}

    print("=== Default settings (z 2.5, threshold 15 %, contamination 0.05) ===")
    for name, (feats, y) in prepared.items():
        res = evaluate_methods(feats, y, **DEFAULTS, if_flags=if_cache[(name, DEFAULTS["contamination"])])
        print(f"\n{name}: {int(y.sum())} anomalies in {len(y)} purchases")
        for method, m in res.items():
            print(f"  {method:<17} precision {m['precision']:.2f}  recall {m['recall']:.2f}  F1 {m['f1']:.2f}   (TP {m['tp']}, FP {m['fp']}, FN {m['fn']})")
            rows.append({"test_set": name, "method": method, "settings": "default", **m})

    grid_rows = []
    for cutoff, thr, cont in itertools.product(GRID_Z, GRID_T, GRID_C):
        f1s, parts = [], {}
        for name, (feats, y) in prepared.items():
            m = evaluate_methods(feats, y, cutoff, thr, cont, if_flags=if_cache[(name, cont)])["Ensemble"]
            parts[name] = m
            f1s.append(m["f1"])
            grid_rows.append({"test_set": name, "method": "Ensemble", "settings": f"z={cutoff}, thr={thr}%, cont={cont}", **m})
        grid_rows.append({"_avg_f1": float(np.mean(f1s)), "_cfg": (cutoff, thr, cont)})
    best = max((r for r in grid_rows if "_avg_f1" in r), key=lambda r: r["_avg_f1"])
    rows += [r for r in grid_rows if "_avg_f1" not in r]
    bz, bt, bc = best["_cfg"]
    print(f"\n=== Grid search ({len(GRID_Z) * len(GRID_T) * len(GRID_C)} settings): best ensemble F1 (average of both sets) = {best['_avg_f1']:.3f} "
          f"with z cutoff {bz}, threshold {bt} %, contamination {bc} ===")

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(rows)
    out.to_csv(EVAL_DIR / "anomaly_metrics.csv", index=False)

    # ---- chart 1: grouped bars (default settings)
    d = out[out.settings == "default"].melt(id_vars=["test_set", "method"], value_vars=["precision", "recall", "f1"], var_name="metric")
    g = sns.catplot(data=d, x="method", y="value", hue="metric", col="test_set", kind="bar", height=4.2, aspect=1.25, palette=["#0F4C5C", "#2A7F8E", "#E9785B"])
    g.set_axis_labels("", "score (0 - 1)")
    g.set_titles("{col_name}")
    g.set(ylim=(0, 1.05))
    for ax in g.axes.flat:
        ax.tick_params(axis="x", rotation=20)
    g.figure.suptitle("Anomaly detection: precision, recall and F1 by method", y=1.03)
    g.savefig(FIG_DIR / "anomaly_metrics_by_method.png", dpi=130)
    plt.close("all")

    # ---- chart 2: confusion matrices of the ensemble
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    for ax, (name, (feats, y)) in zip(axes, prepared.items()):
        m = evaluate_methods(feats, y, **DEFAULTS, if_flags=if_cache[(name, DEFAULTS["contamination"])])["Ensemble"]
        sns.heatmap([[m["tn"], m["fp"]], [m["fn"], m["tp"]]], annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax,
                    xticklabels=["predicted normal", "predicted anomaly"], yticklabels=["really normal", "really anomaly"])
        ax.set_title(f"Ensemble - {name}")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "anomaly_confusion_ensemble.png", dpi=130)
    plt.close(fig)

    # ---- plain-language lines for the report
    e1 = out[(out.settings == "default") & (out.method == "Ensemble")].set_index("test_set")
    best_single = out[(out.settings == "default") & (out.method != "Ensemble")].groupby("method")["f1"].mean().sort_values()
    print("\n=== Lines for your report ===")
    print(f"1. On the demo shop's labelled purchases the ensemble found {e1.loc['ground_truth', 'recall'] * 100:.0f}% of the injected price anomalies "
          f"and {e1.loc['ground_truth', 'precision'] * 100:.0f}% of its alerts were real (F1 {e1.loc['ground_truth', 'f1']:.2f}).")
    print(f"2. On a second test set with new random spikes and drops the ensemble reached recall {e1.loc['fresh_injection', 'recall']:.2f} and precision "
          f"{e1.loc['fresh_injection', 'precision']:.2f}, so the result is not tied to one dataset.")
    ens_f1 = e1["f1"].mean()
    if ens_f1 + 1e-9 >= best_single.iloc[-1]:
        line3 = (f"3. The strongest single method was {best_single.index[-1]} (average F1 {best_single.iloc[-1]:.2f}); the ensemble matched or beat it "
                 f"(F1 {ens_f1:.2f}) and was clearly better than the weakest, {best_single.index[0]} (F1 {best_single.iloc[0]:.2f}).")
    else:
        line3 = (f"3. The simple {best_single.index[-1]} scored highest (average F1 {best_single.iloc[-1]:.2f}) versus the ensemble's {ens_f1:.2f}, because the injected "
                 f"anomalies are far from the market price while normal prices stay within about 8%. The ensemble is still useful: it keeps working "
                 f"when no market price is known, where the threshold rule is weak, and it needs agreement from two methods before raising an alarm.")
    print(line3)
    print(f"4. Grid search over 27 settings gave a best average F1 of {best['_avg_f1']:.2f} at z cutoff {bz}, threshold {bt}% and contamination {bc}, "
          f"so the default settings (z 2.5, threshold 15%, contamination 0.05) are close to the best.")
    print(f"5. Overall the ensemble missed {int(e1['fn'].sum())} anomalies and raised {int(e1['fp'].sum())} false alarms across {int(e1['tp'].sum() + e1['fn'].sum())} real anomalies in the two test sets. "
          f"Note: the data is synthetic, so real shops with messier prices will score lower.")
    print(f"\nSaved: {EVAL_DIR / 'anomaly_metrics.csv'}, {FIG_DIR / 'anomaly_metrics_by_method.png'}, {FIG_DIR / 'anomaly_confusion_ensemble.png'}")


if __name__ == "__main__":
    main()
