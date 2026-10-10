# 7-minute demo script (demo shop "Sharma General Store", login demo@vyapariai.com / demo1234)

**Before you start:** re-seed so dates are current (`python -m app.ml.seed_demo`), start backend and frontend, open the app in a clean browser window (1440x900), log out, close other tabs, silence notifications.
**Backup:** if anything fails, switch to the pre-recorded video; if the internet is down the advisor still answers in offline mode (say so calmly).

| Time | Click path | Say (about) | Backup if it fails |
|---|---|---|---|
| 0:00-0:40 | Login page, type the demo e-mail, log in. Dashboard opens. | "Small shopkeepers decide prices from experience and lose margin. VyapariAI gives them data-driven advice. This is a demo shop in Nagpur with 12 months of data." Point at the 4 cards, then the price trend (market line, forecast, purchase dots). | Refresh the page; the session is kept. |
| 0:40-1:30 | Sidebar **Pricing**. Choose **Soyabean Oil** (or **Rice**). | "Each dot is a purchase, coloured by supplier; the dashed line is the market price. The verdict compares my last price with the market on that day. Potential savings is what I lost by paying above market." Mention the supplier chips: one supplier is always dearer. | Pick another product. |
| 1:30-2:20 | **Purchases** > New Purchase. Product Soyabean Oil, supplier XYZ Wholesale, quantity 10, price about 40 % above the Pricing page's market price. | "While I type the price, a tag tells me it is **Overpaying**." Save: the **unusual price** window opens. "The system checked three methods and flagged it at once." Click **Undo**: "stock is restored." | Show the same on the Alerts page instead. |
| 2:20-3:00 | **Alerts**. Show a High and a Medium alert, the filters and the sidebar badge. Click **Scan now**. | "Alerts come from Z-score, Isolation Forest and a threshold rule voting together; scanning twice never duplicates alerts." Open **View price analysis** on one alert. | Skip the filters. |
| 3:00-3:50 | **Forecast**, product Rice, 14 days. | "The solid line is the past, the dashed line the forecast, the shaded area the likely range. On the right the five models are compared by MAPE; the best is picked per commodity." Say once: "Forecasts are estimates, and our price data is partly synthetic." | Use 7 days. |
| 3:50-5:00 | **Recommendations** > What to buy. Open one **Buy Now** and one **Wait** card; read the reasons aloud. Then **What to sell at**, Milk, move the margin slider to 25 %. | "Every recommendation shows reasons from the shop's own numbers: days of stock left, delivery time, price direction. For selling, the price follows the market but stays between my minimum margin and my target." | Show only the buy tab. |
| 5:00-5:40 | **Suppliers** > Compare, product Rice. | "Best value is the cheapest supplier with enough orders and a steady price, not just the cheapest." | Skip. |
| 5:40-6:40 | **AI Advisor**. Switch to **MR**. Press the **microphone** and ask in Marathi (or type): "तांदळाचा भाव वाजवी आहे का?" Open **Sources used**. Press the speaker icon. | "The advisor retrieves real numbers from this shop and only talks about them. If a price in the answer is not in the data, the answer is blocked. Offline it still gives a basic answer." | Type the question; if the AI is offline say "this is the offline answer; the numbers are the same". |
| 6:40-7:00 | Back to Dashboard. | "Built with React, FastAPI, scikit-learn and Gemini; 450 automated tests; ready for PostgreSQL. Thank you." | |

**Rehearse twice with a stopwatch. Questions to expect are in `viva_sheet.md`.**
