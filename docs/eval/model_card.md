# Model card - VyapariAI price forecasting and anomaly detection

Generated 2026-10-09 from the real result files. Numbers below come from `forecast_metrics.csv` and `anomaly_metrics.csv`.

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
- **Results:** selected models have a mean MAPE of 0.72%; they beat the naive baseline on 15 of 15 commodities. Wins: Linear Regression 2, Random Forest 1, Holt-Winters 12.
- **Confidence band:** price +/- 1.28 x residual standard deviation x square root of the step (about 80 %).
- **Confidence label in the app:** High if MAPE < 3 %, Medium < 6 %, otherwise Low.

## Anomaly detection
- **Methods:** Z-score (against the product's own last 90 days), Isolation Forest (per product when it has 30+ purchases), and a threshold rule (% away from the market price). A purchase is flagged when 2 of 3 agree, or when it is more than 25 % off the market.
- **Results at default settings:** ground_truth: precision 0.96, recall 0.96, F1 0.96; fresh_injection: precision 1.00, recall 0.96, F1 0.98.
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
