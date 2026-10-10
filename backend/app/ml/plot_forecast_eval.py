"""
plot_forecast_eval.py - charts for the forecast evaluation (saved to docs/figures/).

    python -m app.ml.plot_forecast_eval

(a) forecast_actual_vs_pred_<commodity>.png : actual price vs the best model's 7-day-ahead paths over the test window
(b) forecast_mape_by_model.png              : grouped bars, MAPE of every model for every commodity
Run python -m app.ml.train_forecast first (it writes docs/eval/forecast_metrics.csv).
"""
import re
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from app.database import SessionLocal
from app.ml.features import load_series
from app.ml.train_forecast import EVAL_DIR, evaluate_commodity

warnings.filterwarnings("ignore")
FIG_DIR = EVAL_DIR.parent / "figures"
sns.set_theme(style="whitegrid")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def plot_mape_bars(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(13, 5))
    sns.barplot(data=df, x="commodity", y="mape", hue="model", ax=ax, palette="viridis")
    ax.set_ylabel("MAPE % (7-day ahead, lower is better)")
    ax.set_xlabel("")
    ax.set_title("Forecast error by model and commodity")
    plt.xticks(rotation=40, ha="right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "forecast_mape_by_model.png", dpi=130)
    plt.close(fig)


def plot_actual_vs_pred(db, commodity: str, best: str) -> None:
    series = load_series(db, commodity)
    ev = evaluate_commodity(series)
    test = series[series.index >= ev["test_start"]]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(test.index, test.values, color="#243238", lw=1.6, label="actual")
    for i, (origin, _actual, path) in enumerate(ev["paths"][best]):
        days = pd.date_range(origin, periods=len(path), freq="D")
        ax.plot(days, path, color="#E9785B", lw=1.6, alpha=0.85, label=f"{best} (7-day forecasts)" if i == 0 else None)
    ax.set_title(f"{commodity}: actual vs {best} forecasts on the test window (Rs per unit)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"forecast_actual_vs_pred_{slug(commodity)}.png", dpi=130)
    plt.close(fig)


def main() -> None:
    csv = EVAL_DIR / "forecast_metrics.csv"
    if not csv.exists():
        raise SystemExit("Run python -m app.ml.train_forecast first.")
    df = pd.read_csv(csv)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plot_mape_bars(df)
    db = SessionLocal()
    try:
        for commodity, best in df[df.is_best].set_index("commodity")["model"].items():
            plot_actual_vs_pred(db, commodity, best)
    finally:
        db.close()
    print(f"Charts saved in {FIG_DIR}")


if __name__ == "__main__":
    main()
