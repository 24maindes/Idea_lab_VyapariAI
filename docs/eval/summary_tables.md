# Evaluation summary tables

Generated on 2026-10-09 from `forecast_metrics.csv` and `anomaly_metrics.csv`. Do not edit by hand: run `python scripts/make_eval_docs.py`.

## 1. Price forecasting (7 days ahead, rolling-origin evaluation)

### Best model per commodity

| Commodity | Best model | MAPE % | RMSE (Rs) |
|---|---|---|---|
| Chana | Holt-Winters | 0.76 | 0.80 |
| Milk | Holt-Winters | 0.65 | 0.39 |
| Moong Dal | Holt-Winters | 0.57 | 0.78 |
| Mustard Oil | Holt-Winters | 0.59 | 1.09 |
| Onion | Holt-Winters | 0.81 | 0.28 |
| Paneer | Linear Regression | 0.71 | 3.52 |
| Potato | Holt-Winters | 0.88 | 0.30 |
| Rice | Linear Regression | 0.60 | 0.29 |
| Salt | Holt-Winters | 0.81 | 0.21 |
| Soyabean Oil | Random Forest | 0.79 | 1.25 |
| Sugar | Holt-Winters | 0.54 | 0.26 |
| Tea | Holt-Winters | 0.61 | 1.00 |
| Tomato | Holt-Winters | 1.07 | 0.43 |
| Toor Dal | Holt-Winters | 0.74 | 1.33 |
| Wheat Atta | Holt-Winters | 0.74 | 0.30 |

### MAPE of every model (lower is better)

| Commodity | Naive (tomorrow = today) | Linear Regression | Random Forest | XGBoost | Holt-Winters |
|---|---|---|---|---|---|
| Chana | 1.23 | 0.87 | 1.74 | 2.41 | 0.76 |
| Milk | 0.80 | 0.91 | 0.86 | 0.96 | 0.65 |
| Moong Dal | 0.82 | 0.58 | 1.04 | 1.11 | 0.57 |
| Mustard Oil | 0.85 | 0.60 | 0.72 | 0.73 | 0.59 |
| Onion | 0.99 | 1.07 | 1.63 | 1.88 | 0.81 |
| Paneer | 0.98 | 0.71 | 1.02 | 1.49 | 0.81 |
| Potato | 1.56 | 0.97 | 1.47 | 1.45 | 0.88 |
| Rice | 0.76 | 0.60 | 0.72 | 1.02 | 0.60 |
| Salt | 0.98 | 0.85 | 0.96 | 1.00 | 0.81 |
| Soyabean Oil | 0.89 | 0.82 | 0.79 | 0.81 | 0.79 |
| Sugar | 0.73 | 0.56 | 0.73 | 1.23 | 0.54 |
| Tea | 0.79 | 0.65 | 0.79 | 0.82 | 0.61 |
| Tomato | 1.76 | 1.27 | 1.59 | 1.62 | 1.07 |
| Toor Dal | 1.02 | 0.81 | 1.70 | 1.86 | 0.74 |
| Wheat Atta | 0.92 | 0.79 | 0.81 | 1.25 | 0.74 |

### Average over all commodities

| Model | Average MAPE % | Average RMSE (Rs) |
|---|---|---|
| Naive (tomorrow = today) | 1.01 | 1.08 |
| Linear Regression | 0.80 | 0.86 |
| Random Forest | 1.10 | 1.19 |
| XGBoost | 1.31 | 1.44 |
| Holt-Winters | 0.73 | 0.84 |

### How often each model won

| Model | Commodities won |
|---|---|
| Naive (tomorrow = today) | 0 |
| Linear Regression | 2 |
| Random Forest | 1 |
| XGBoost | 0 |
| Holt-Winters | 12 |

The selected model beat the naive baseline on **15 of 15** commodities. The mean MAPE of the selected models is **0.72%**.

## 2. Anomaly detection (purchase prices)

| Test set | Method | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| ground_truth | Z-score | 0.48 | 0.64 | 0.55 | 16 | 17 | 9 |
| ground_truth | Isolation Forest | 0.73 | 0.88 | 0.80 | 22 | 8 | 3 |
| ground_truth | Threshold rule | 1.00 | 1.00 | 1.00 | 25 | 0 | 0 |
| ground_truth | Ensemble | 0.96 | 0.96 | 0.96 | 24 | 1 | 1 |
| fresh_injection | Z-score | 0.50 | 0.76 | 0.60 | 19 | 19 | 6 |
| fresh_injection | Isolation Forest | 0.70 | 0.84 | 0.76 | 21 | 9 | 4 |
| fresh_injection | Threshold rule | 1.00 | 0.96 | 0.98 | 24 | 0 | 1 |
| fresh_injection | Ensemble | 1.00 | 0.96 | 0.98 | 24 | 0 | 1 |

Grid search over 27 settings: best average ensemble F1 = **0.980** with `z=3.0, thr=10%, cont=0.08`.
