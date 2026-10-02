"""
build_demand_profile.py   (MICRO layer of VyapariAI)
----------------------------------------------------
Reads the retail / transaction datasets and extracts a small DEMAND PROFILE that
seed_demo.py uses to simulate the shop's sales. Output: backend/data/demand_profile.json

    python -m app.ml.build_demand_profile

What we take from each dataset (and what we deliberately do NOT take):

  whole_sale_customers_data.csv  (440 wholesale clients, yearly spend per category)
      -> category_share: how a typical buyer splits money across Fresh / Milk / Grocery /
         Detergents ... Used to give categories realistic RELATIVE sales volumes.

  supermarket_data.csv           (UCI Online Retail, 540k invoice lines, 2010-11)
      -> demand_noise: how much weekly demand of a single item wobbles around its average.
      -> month_index: relative monthly demand (the Oct-Dec peak shows a festive season).
      NOT used for weekday pattern: this shop has no Saturday invoices at all, so it would
      tell us nothing about a kirana's weekends.

  online_sales_dataset.csv       (synthetic Kaggle data, 2020-25, dirty values)
      -> only cleaned and used as a cross-check of the typical order-size distribution
         (median units per line). Rows with negative qty/price are dropped.

Weekend uplift and Indian festival bumps are BUSINESS ASSUMPTIONS (see seed_demo.py),
because none of these datasets is from an Indian neighbourhood shop.
If a raw file is missing we silently fall back to defaults, so the project never breaks.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BACKEND_DIR / "data" / "raw"
OUT_JSON = BACKEND_DIR / "data" / "demand_profile.json"

# used when a raw file is missing, and as the baseline in tests
DEFAULT_PROFILE = {
    "category_share": {"Fresh": 0.36, "Milk": 0.17, "Grocery": 0.24, "Frozen": 0.09,
                       "Detergents_Paper": 0.09, "Delicassen": 0.05},
    "demand_noise": 0.25,
    "month_index": {str(m): 1.0 for m in range(1, 13)},
    "median_order_units": 3,
    "sources": [],
}


def _find(pattern: str) -> Path | None:
    files = sorted(RAW_DIR.rglob(pattern))
    return files[0] if files else None


def from_wholesale_customers(profile: dict) -> None:
    f = _find("whole_sale_customers*.csv")
    if f is None:
        return
    df = pd.read_csv(f)
    cols = ["Fresh", "Milk", "Grocery", "Frozen", "Detergents_Paper", "Delicassen"]
    totals = df[cols].sum()
    profile["category_share"] = (totals / totals.sum()).round(3).to_dict()
    profile["sources"].append(f.name)


def from_supermarket(profile: dict) -> None:
    f = _find("supermarket_data.csv")
    if f is None:
        return
    df = pd.read_csv(f, encoding="latin1", usecols=["Invoice", "StockCode", "Quantity", "InvoiceDate", "Price"])
    # clean: drop cancellations (invoice starts with C), negative / zero qty and price
    df = df[~df["Invoice"].astype(str).str.startswith("C")]
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]
    df["dt"] = pd.to_datetime(df["InvoiceDate"], format="%d/%m/%y %H:%M", errors="coerce")
    df = df.dropna(subset=["dt"])

    # (a) monthly index: units per month / average month (Dec-2011 is incomplete -> use 2011 only
    #     for Jan-Nov and 2010 for December)
    monthly = df.groupby([df["dt"].dt.year, df["dt"].dt.month])["Quantity"].sum()
    by_month = {}
    for m in range(1, 13):
        year = 2010 if m == 12 else 2011
        by_month[m] = monthly.get((year, m), np.nan)
    s = pd.Series(by_month).astype(float)
    s = s / s.mean()
    profile["month_index"] = {str(m): round(float(v), 3) for m, v in s.items()}

    # (b) demand noise: coefficient of variation of WEEKLY units of the 40 best-selling items.
    #     Bulk one-off orders (top 1 % of a day's quantity) are removed first.
    top = df.groupby("StockCode")["Quantity"].sum().nlargest(40).index
    cvs = []
    for code in top:
        d = df[df["StockCode"] == code]
        d = d[d["Quantity"] < d["Quantity"].quantile(0.99)]
        weekly = d.set_index("dt")["Quantity"].resample("W").sum()
        weekly = weekly[weekly > 0]
        if len(weekly) >= 20:
            cvs.append(weekly.std() / weekly.mean())
    if cvs:
        # clip: a corner shop is less volatile than UK gift wholesalers, but never perfectly stable
        profile["demand_noise"] = round(float(np.clip(np.median(cvs) * 0.5, 0.15, 0.40)), 3)
    profile["sources"].append(f.name)


def from_online_sales(profile: dict) -> None:
    f = _find("online_sales_dataset.csv")
    if f is None:
        return
    df = pd.read_csv(f, usecols=["Quantity", "UnitPrice"])
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]     # dirty file: negatives exist
    profile["median_order_units"] = int(df["Quantity"].median())
    profile["sources"].append(f.name)


def main() -> None:
    profile = json.loads(json.dumps(DEFAULT_PROFILE))   # deep copy
    from_wholesale_customers(profile)
    from_supermarket(profile)
    from_online_sales(profile)
    OUT_JSON.write_text(json.dumps(profile, indent=2))
    print(json.dumps(profile, indent=2))
    print(f"\nSaved -> {OUT_JSON}")


if __name__ == "__main__":
    main()
