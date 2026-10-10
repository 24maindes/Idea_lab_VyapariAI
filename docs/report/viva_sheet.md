# Viva sheet: 25 likely questions (answers are short on purpose; say them in your own words)

## About the project
1. **What problem does it solve?** Small shopkeepers decide purchase and selling prices from experience, so they overpay suppliers and stock badly. VyapariAI compares prices with the market, forecasts, warns about abnormal prices and recommends what to buy and sell at.
2. **Why is it different from existing systems?** Most tools are for large retailers with big clean data. This one is lightweight, for one shop, and combines fair-price analysis, forecasting, anomaly detection, a decision engine and a grounded multilingual advisor.
3. **What is the data? Is it real?** Market price movement comes from the real India WPI index, converted to rupees with assumed anchor prices and date-shifted; recent months and Paneer are generated. The shop data is synthetic. So results show the method, not real-world accuracy.
4. **Why a date shift?** The WPI ends in May 2017; the demo needs prices up to today. We shifted by whole years and generated the small remaining gap. It is documented in `data_sources.md`.

## ML and forecasting
5. **Which model is best and why?** Per commodity the lowest MAPE wins; Holt-Winters wins 12 of 15, Linear Regression 2, Random Forest 1. The series are smooth and seasonal, which suits exponential smoothing.
6. **XGBoost was in your synopsis. Why did it lose?** On smooth data with small noise tree models have little to learn and cannot extrapolate; we measured it and report it honestly. We keep all five models and choose per commodity.
7. **What is MAPE and RMSE?** MAPE = average absolute error in percent (easy to explain). RMSE = root of the mean squared error in rupees, punishes big misses.
8. **How did you avoid data leakage?** Rolling features are computed on the series shifted by one day, so day t never sees its own price; the split is chronological; evaluation uses a rolling origin. A unit test proves it.
9. **Why not shuffle the data?** Shuffling would let the model see the future of the same series and give fake accuracy.
10. **How is the confidence band computed?** Price +/- 1.28 x the residual standard deviation x square root of the step: about 80 % and wider further ahead.
11. **Why is the naive model so close?** Prices change little day to day, so "tomorrow = today" is a strong baseline; our selected models still beat it on 15 of 15 commodities, but only by a few tenths of a percent.

## Anomaly detection
12. **How does anomaly detection work?** Z-score (against the product's own last 90 days), Isolation Forest, and a threshold rule vs the market price vote; two of three flag it, or more than 25 % off the market flags alone.
13. **Why three methods?** Each makes different mistakes: Z-score is noisy, Isolation Forest needs data, the threshold needs a market price. Voting reduces false alarms and works with missing market data.
14. **The threshold rule scored higher than the ensemble. Why keep the ensemble?** Our injected anomalies are 20-45 % away, so a simple rule finds them. The ensemble is more robust when no market price exists and for subtler cases; we say this in the report.
15. **How good is it?** On the labelled demo purchases the ensemble had precision 0.96, recall 0.96, F1 0.96; on a second test set with new injections F1 0.98. These are synthetic anomalies.

## Decision engine and prices
16. **How does Buy Now / Buy Limited / Wait work?** Rules in order: stockout risk, rising price with low stock, falling price with enough stock, bad price, enough stock, otherwise a limited top-up. Quantity = shortfall to the target stock (days of sales x cover days). All numbers are in `config.py`.
17. **What if there is no sales history?** The reorder level replaces the sales speed and the answer carries a note "No sales history - using reorder level".
18. **How is the selling price computed?** Cost = weighted average of the last 5 purchases; floor = cost + minimum margin; target = cost + target margin; the market retail price is clamped between them; the range is 0.97x to 1.05x.
19. **What does "fair price" mean?** (price paid - market price) / market price: Great deal at -3 % or lower, Fair up to +3 %, Slightly high up to +8 %, Overpaying above.

## The AI advisor
20. **What is RAG here?** Retrieve the shop's real numbers with structured SQL/Pandas services, put them into the prompt, let Gemini answer only from them. We did not use a vector database because the data is numeric tables, not text.
21. **How do you stop hallucinations?** Strict prompt rules, temperature 0.2, a numeric check (every price in the answer must exist in the context within 1 %), one stricter retry and then an offline template answer; sources are shown.
22. **What if Gemini is down or has no key?** A template answer in the chosen language with the same numbers, marked "Basic answer (AI offline)".
23. **How is Hindi/Marathi handled?** The question is understood by a dictionary of product names and topic words in both scripts and Latin spelling; the prompt asks the model to answer in the chosen language. Voice uses the browser's speech recognition and synthesis.

## Engineering
24. **How do you keep one shop's data private?** Every table has `shop_id`; the shop id comes from the login token, never from the request; every query filters by it; tests try other shops' ids on every endpoint and expect 404.
25. **How did you test it?** 450 automated tests (all on SQLite, 442 also on PostgreSQL), a 22-step end-to-end script, a 23-check browser-style smoke test, and a manual bug-bash checklist. **Limitations?** Partly synthetic data, 7-14 day forecasts, in-memory caches for one server, no migrations, advisor quality with the real model judged manually.
