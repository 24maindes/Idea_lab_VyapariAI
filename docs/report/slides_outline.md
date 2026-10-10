# 10-slide outline (one idea per slide; keep text short, use screenshots)

| # | Title | Content | Visual |
|---|---|---|---|
| 1 | VyapariAI | Name, tagline "AI price and purchase advisor for local shopkeepers", team, guide, university, IDEA Lab | Logo / dashboard screenshot |
| 2 | The problem | Shopkeepers decide on experience: overpay suppliers, bad stock, low margin. 4 questions they cannot answer | 4 icons (fair price? price rising? how much? sell at?) |
| 3 | The solution and objectives | The 6 synopsis objectives, one line each, with a tick | Architecture diagram (`README.md`) |
| 4 | Data | WPI index (real) -> rupees, synthetic tail, synthetic demo shop; honest note | Table real vs synthetic |
| 5 | Fair price and anomalies | Variance rule, 3-method voting, instant warning | `04_purchase_fair_price_tag.png`, `05_anomaly_popup.png`, F1 table |
| 6 | Forecasting | 5 models, rolling-origin evaluation, no leakage; result: Holt-Winters 12/15, XGBoost worst | `forecast_mape_by_model.png`, `07_forecast.png` |
| 7 | Decisions | Buy Now / Limited / Wait with reasons; selling price range; supplier comparison | `09_recommendations_buy.png`, `10_selling_price.png` |
| 8 | AI advisor (RAG) | 7-step pipeline, grounding check, fallback, EN/HI/MR, voice | `12_advisor_marathi.png` + pipeline diagram |
| 9 | Quality | 450 tests, 22-step e2e, PostgreSQL, security checks, limits stated honestly | Numbers on one slide |
| 10 | Conclusion and future work | What was delivered; limits (synthetic data); next: real mandi data, demand forecasting, WhatsApp, mobile | Thank you + contact |

Speaker notes: practise 1 minute per slide; slide 6 and slide 9 are where examiners ask questions (see `viva_sheet.md`).
