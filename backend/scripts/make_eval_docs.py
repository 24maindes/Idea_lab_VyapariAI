"""
make_eval_docs.py - writes the evaluation documents for the project report FROM THE REAL RESULT FILES (nothing is typed by hand).

    python scripts/make_eval_docs.py          (from the backend folder)

reads   docs/eval/forecast_metrics.csv   (python -m app.ml.train_forecast)
        docs/eval/anomaly_metrics.csv    (python -m app.ml.evaluate_anomaly)
        docs/eval/e2e_timings.json       (python scripts/e2e_flow.py)       optional
writes  docs/eval/summary_tables.md, docs/eval/model_card.md, docs/eval/performance.md
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd

EVAL = Path(__file__).resolve().parents[2] / "docs" / "eval"
LABEL = {"naive": "Naive (tomorrow = today)", "linear": "Linear Regression", "rf": "Random Forest", "xgb": "XGBoost", "holt_winters": "Holt-Winters"}


def md_table(df: pd.DataFrame, floatfmt: str = "{:.2f}") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(floatfmt.format(v) if isinstance(v, float) else str(v) for v in r.tolist()) + " |")
    return "\n".join(lines)


def forecast_section(fm: pd.DataFrame) -> tuple[str, dict]:
    best = fm[fm.is_best].sort_values("commodity")[["commodity", "model", "mape", "rmse"]].copy()
    best["model"] = best["model"].map(LABEL)
    best.columns = ["Commodity", "Best model", "MAPE %", "RMSE (Rs)"]
    wide = fm.pivot(index="commodity", columns="model", values="mape")[["naive", "linear", "rf", "xgb", "holt_winters"]]
    wide.columns = [LABEL[c] for c in wide.columns]
    wide = wide.reset_index().rename(columns={"commodity": "Commodity"})
    avg = fm.groupby("model")[["mape", "rmse"]].mean().reindex(["naive", "linear", "rf", "xgb", "holt_winters"])
    avg_tbl = avg.reset_index()
    avg_tbl["model"] = avg_tbl["model"].map(LABEL)
    avg_tbl.columns = ["Model", "Average MAPE %", "Average RMSE (Rs)"]
    wins = fm[fm.is_best].groupby("model").size().reindex(["naive", "linear", "rf", "xgb", "holt_winters"]).fillna(0).astype(int)
    wins_tbl = pd.DataFrame({"Model": [LABEL[i] for i in wins.index], "Commodities won": wins.values})
    naive = fm[fm.model == "naive"].set_index("commodity")["mape"]
    bestm = fm[fm.is_best].set_index("commodity")["mape"]
    beat = int((bestm < naive.reindex(bestm.index)).sum())
    facts = {"n": len(best), "beat_naive": beat, "avg": avg, "wins": wins, "best_mape_mean": float(bestm.mean())}
    text = ("## 1. Price forecasting (7 days ahead, rolling-origin evaluation)\n\n### Best model per commodity\n\n" + md_table(best, "{:.2f}") +
            "\n\n### MAPE of every model (lower is better)\n\n" + md_table(wide, "{:.2f}") +
            "\n\n### Average over all commodities\n\n" + md_table(avg_tbl, "{:.2f}") +
            "\n\n### How often each model won\n\n" + md_table(wins_tbl) +
            f"\n\nThe selected model beat the naive baseline on **{beat} of {len(best)}** commodities. The mean MAPE of the selected models is "
            f"**{facts['best_mape_mean']:.2f}%**.\n")
    return text, facts


def anomaly_section(am: pd.DataFrame) -> tuple[str, dict]:
    d = am[am.settings == "default"][["test_set", "method", "precision", "recall", "f1", "tp", "fp", "fn"]].copy()
    d.columns = ["Test set", "Method", "Precision", "Recall", "F1", "TP", "FP", "FN"]
    grid = am[am.settings != "default"]
    top = ""
    if len(grid):
        g = grid.groupby("settings")["f1"].mean().sort_values(ascending=False)
        top = f"\n\nGrid search over {len(g)} settings: best average ensemble F1 = **{g.iloc[0]:.3f}** with `{g.index[0]}`."
    ens = d[d["Method"] == "Ensemble"]
    return "## 2. Anomaly detection (purchase prices)\n\n" + md_table(d, "{:.2f}") + top + "\n", {"ens": ens}


def write_summary(fm, am) -> dict:
    ftext, facts = forecast_section(fm)
    atext, afacts = anomaly_section(am)
    (EVAL / "summary_tables.md").write_text(f"# Evaluation summary tables\n\nGenerated on {date.today().isoformat()} from `forecast_metrics.csv` and `anomaly_metrics.csv`. "
                                            f"Do not edit by hand: run `python scripts/make_eval_docs.py`.\n\n{ftext}\n{atext}", encoding="utf-8")
    return {**facts, **afacts}


def write_model_card(fm, am, facts) -> None:
    ens = facts["ens"]
    ens_line = "; ".join(f"{r['Test set']}: precision {r['Precision']:.2f}, recall {r['Recall']:.2f}, F1 {r['F1']:.2f}" for _, r in ens.iterrows())
    wins = ", ".join(f"{LABEL[m]} {int(n)}" for m, n in facts["wins"].items() if n)
    (EVAL / "model_card.md").write_text(f"""# Model card - VyapariAI price forecasting and anomaly detection

Generated {date.today().isoformat()} from the real result files. Numbers below come from `forecast_metrics.csv` and `anomaly_metrics.csv`.

## Purpose
Help a small shopkeeper decide **when and how much to buy** by (1) forecasting the market price of a commodity for the next 7-14 days and
(2) flagging purchase prices that are unusually far from the market. The output is **decision support, not a guarantee**.

## Data
| Item | Source | Real or synthetic |
|---|---|---|
| Market price level and movement | India Wholesale Price Index (WPI, 2011-12 base, Apr 2011 - May 2017) converted from an index to Rs per unit with an ASSUMED present-day anchor price | **Real shape, assumed level**; dates shifted forward by whole years |
| Last months up to today, and Paneer | seeded random generator (trend, yearly wave, weekly wobble, shocks) | **Synthetic** |
| Shop purchases and sales for the demo shop | `seed_demo.py` (fixed seed) with injected anomalies | **Synthetic** |
| Sales pattern (category share, noise, monthly index) | UCI wholesale customers and online retail datasets, as statistics only | Real statistics, used loosely |
See `docs/data_sources.md` for the full table and the cleaning rules.

## Forecast model
- **Target:** wholesale price on day t. **Horizon:** 7 days (14 days by repeating the one-step forecast).
- **Features (14):** price lags 1, 7, 14, 28; rolling mean over 7, 14, 30 days; rolling standard deviation over 7, 14 days; % change over the last week; day of week; month; sine and cosine of the day of year.
- **Leakage prevention:** every rolling feature is computed on the series shifted by one day, so day t never sees its own price. A test proves that changing today's price does not change today's features.
- **Candidates:** naive (tomorrow = today), Linear Regression, Random Forest (300 trees), XGBoost (400 shallow trees), Holt-Winters. The ML models predict the **% change from yesterday**, then convert back to a price (trees cannot output prices larger than they saw in training).
- **Split:** chronological. The last max(60 days, 20 %) is the test period. Time series are never shuffled.
- **Evaluation:** rolling origin. Every 7 days of the test period we pretend that day is "today", use only earlier data, forecast the next 7 days and compare with what happened; errors are averaged over all origins.
- **Metrics:** MAPE (average % error, easy to explain) and RMSE (in rupees, punishes big misses). Selection by lowest MAPE.
- **Results:** selected models have a mean MAPE of {facts['best_mape_mean']:.2f}%; they beat the naive baseline on {facts['beat_naive']} of {facts['n']} commodities. Wins: {wins}.
- **Confidence band:** price +/- 1.28 x residual standard deviation x square root of the step (about 80 %).
- **Confidence label in the app:** High if MAPE < 3 %, Medium < 6 %, otherwise Low.

## Anomaly detection
- **Methods:** Z-score (against the product's own last 90 days), Isolation Forest (per product when it has 30+ purchases), and a threshold rule (% away from the market price). A purchase is flagged when 2 of 3 agree, or when it is more than 25 % off the market.
- **Results at default settings:** {ens_line}.
- Test sets: the demo shop's labelled purchases, and a second set with new random spikes and drops injected into the clean purchases.

## Limitations
- The price series is **partly synthetic**, so accuracy on real mandi prices will be lower and must be re-measured.
- A flat, smooth series makes the naive model hard to beat; real prices with festivals, weather and policy shocks are harder.
- Forecasts say nothing about events the model has not seen (floods, export bans). Never treat them as promises.
- Only wholesale/retail levels at national scale: no local market differences.
- Shops with few purchases get fewer anomaly votes (the z-score needs 5 earlier purchases).

## Retraining
1. `python -m app.ml.build_reference` and `python -m app.ml.load_reference` (new reference data)
2. `python -m app.ml.train_forecast` (all commodities) or `--commodity Rice`; or the **Retrain models** button on the Forecast page
3. The new model replaces the old file only after it was fully written; if training fails the old model stays.
4. `python -m app.ml.evaluate_anomaly` and `python scripts/make_eval_docs.py` to refresh the documents.

## Ethical note
Forecasts and recommendations are **estimates to support a decision**, not financial advice or a guarantee of profit. The shopkeeper stays
responsible for the decision. Every recommendation shows its reasons and data quality so it can be checked. Shop data is private: every query is
filtered by the logged-in shop and no data from one shop is ever used in another shop's answers.
""", encoding="utf-8")


def write_performance() -> None:
    f = EVAL / "e2e_timings.json"
    if f.exists():
        data = json.loads(f.read_text(encoding="utf-8"))
        rows = "\n".join(f"| {s['step']} | {s['ms']:.0f} | {'PASS' if s['ok'] else 'FAIL'} |" for s in data["steps"])
        total = sum(s["ms"] for s in data["steps"])
        body = (f"Measured on {data['date']} against `{data['server']}` by `scripts/e2e_flow.py` (one request per step, includes the first call after a restart).\n\n"
                f"| Step | Response time (ms) | Result |\n|---|---|---|\n{rows}\n\n**Total:** {total / 1000:.1f} s for {len(data['steps'])} steps. "
                f"First recommendations call includes loading the saved models.\n")
    else:
        body = "[TODO: run `python scripts/e2e_flow.py` first, then `python scripts/make_eval_docs.py`]\n"
    (EVAL / "performance.md").write_text(f"""# Performance (1 page)

**Machine / server:** [TODO: CPU, RAM, hosting]  **Database:** [TODO: SQLite / PostgreSQL]

{body}
**Targets:** simple reads under 200 ms, dashboard under 1 s, advisor answer under 8 s with Gemini (the offline answer is instant).
**Caching:** forecasts 10 min, recommendations and dashboard heavy part 60 s, advisor context 60 s; every write of a shop clears that shop's cache.
""", encoding="utf-8")


def main() -> None:
    fm = pd.read_csv(EVAL / "forecast_metrics.csv")
    am = pd.read_csv(EVAL / "anomaly_metrics.csv")
    facts = write_summary(fm, am)
    write_model_card(fm, am, facts)
    write_performance()
    print("Wrote summary_tables.md, model_card.md and performance.md in", EVAL)


if __name__ == "__main__":
    main()
