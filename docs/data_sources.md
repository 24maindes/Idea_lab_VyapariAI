# VyapariAI - Data Sources

VyapariAI uses two layers of data (fill in the `TODO` cells before submission).

| Layer | Purpose |
|---|---|
| **Macro** (market benchmark) | Reference market prices: fair-price checks, price forecasting, anomaly detection |
| **Micro** (shop behaviour) | Simulated shop sales: stock flow, demand pattern, stock turnover |

## 1. Source table

| # | Source name | File in `backend/data/raw` | URL | Licence | Commodities / what we use | Real or synthetic |
|---|---|---|---|---|---|---|
| 1 | India Wholesale Price Index (WPI) 2011-12 base, Apr-2011 to May-2017 | `WPI-2011-12-May2017.csv` | TODO (Kaggle / eaindustry.nic.in link) | TODO | Rice, Wheat Atta, Sugar, Toor Dal (Arhar), Chana (Gram), Moong Dal, Onion, Potato, Tomato, Milk, Soyabean Oil, Mustard Oil, Salt, Tea | **Real index, converted to Rs** (see section 2) |
| 2 | Synthetic generator `make_synthetic_reference.py` | - (code only) | n/a | n/a (our own code) | Paneer (not in WPI) and the short tail between the shifted WPI data and today for all other commodities | **Synthetic** (seeded) |
| 3 | Wholesale customers data (Portugal, 440 clients) | `whole_sale_customers_data.csv` | TODO (UCI ML Repository link) | TODO | Share of spend by category (Fresh / Milk / Grocery ...) -> splits the shop's daily sales budget | Real data, used for **proportions only** |
| 4 | Online Retail "Supermarket" dataset (UK, 2010-11, 540k lines) | `supermarket_data.csv` | TODO (UCI ML Repository link) | TODO | Monthly demand index and day-to-day demand noise | Real data, used for **statistics only** |
| 5 | Online Shopping Patterns & Retail Performance (Kaggle) | `online_sales_dataset.csv` | TODO | TODO | Cleaned and read for a typical order-size cross-check only (not used in the seed) | Appears synthetic (contains negative quantities and typos); **not used for prices** |
| 6 | Demo shop data (`seed_demo.py`) | - (code only) | n/a | n/a | 12 months of purchases and sales of "Sharma General Store" | **Synthetic** (seed 42) |

## 2. Honest notes (be ready to explain these in the viva)

1. **WPI is an index, not a price.** It is monthly, base 2011-12 = 100. We convert it with
   `price(t) = anchor_price x index(t) / index(last month)`. The real, data-driven part is the *shape*
   of price movement. The `anchor_price` per commodity (in `build_reference.py`, dict `COMMODITIES`) is an
   **assumed** present-day wholesale price. Replace it with real Agmarknet/mandi prices if you have them.
2. **Monthly to daily.** Linear interpolation between months plus a tiny weekly wobble and daily noise (seeded).
3. **Date shift.** The WPI file ends in May 2017. We shift all dates forward by whole years (auto: +9) so the data ends near today,
   and fill the small remaining gap with synthetic data. Consequence: the dates are not the historical dates.
   Use `python -m app.ml.build_reference --shift-years 0 --no-extend` to keep the original dates (the demo shop then has no data for today).
4. **Retail price** = wholesale x 1.10 to 1.15 (assumption, same as the synthetic generator).
5. **Weekend uplift and festival bumps** in the demo sales are business assumptions (`seed_demo.py`), because none of the
   datasets comes from an Indian neighbourhood shop. The UCI retail data has no Saturday invoices, so it cannot give a weekday pattern.
6. **Demo anomalies** are injected (21 spikes of +20 to +45 %, 4 drops of -20 to -30 %) and recorded in `backend/data/anomaly_ground_truth.csv`,
   which is the answer key for evaluating the anomaly detector (precision / recall).

## 3. Cleaning rules applied to the WPI file

| Rule | How |
|---|---|
| Parse dates | month headers like `Apr-11` to a date (15th of the month) |
| Strip commas | thousands separators removed before converting to numbers |
| Remove duplicates | duplicate rows and repeated commodity names dropped |
| Typo outliers | a month more than 3x (or under 1/3) of the median of its 5 neighbouring months is removed and re-filled. 3x because real vegetable spikes (tomato, onion) can double within a month |
| Fill gaps | interpolation across at most one missing month, then forward-fill of at most 3 days |
| Short series | commodities with less than 12 months are dropped |
| Encoding | the file contains a Windows-1252 byte, read with a utf-8 to cp1252 fallback |
