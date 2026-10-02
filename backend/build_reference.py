"""
build_reference.py   (MACRO layer of VyapariAI)
-----------------------------------------------
Reads the real India Wholesale Price Index (WPI) file and writes
backend/data/reference_prices.csv with the columns:

    commodity, market, price_date, wholesale_price, retail_price, unit, source

Run from the backend folder:
    python -m app.ml.build_reference

IMPORTANT - what the raw data really is
  * The WPI file is a MONTHLY INDEX (base 2011-12 = 100), NOT a price in Rs/kg.
  * It covers Apr-2011 .. May-2017 only.
So we do three honest conversions, all explained in docs/data_sources.md:

  1. INDEX -> RUPEES:  price(t) = ANCHOR_PRICE x index(t) / index(last month).
     ANCHOR_PRICE is an assumed current wholesale price (see COMMODITIES below).
     The real part is the SHAPE of the price movement (rises, falls, seasonality).
  2. MONTHLY -> DAILY: linear interpolation between monthly points, plus a tiny
     weekly wobble and daily noise (seeded) so it looks like daily mandi data.
  3. DATE SHIFT: the whole series is shifted forward by whole years (default 9) so
     that it ends close to today. Without this the demo shop (12 months up to today)
     would have no reference prices. The small gap to today is filled with the
     synthetic generator. Use --shift-years 0 --no-extend to keep the original dates.

Cleaning steps (as required): parse dates, strip commas, remove duplicate rows,
remove typo outliers, forward-fill gaps of up to 3 days, drop commodities with
less than 12 months of data.
"""
import argparse
import re
import zlib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.make_synthetic_reference import MARKET_NAME, generate_commodity

# ---------------------------------------------------------------- paths
BACKEND_DIR = Path(__file__).resolve().parents[2]      # .../backend
RAW_DIR = BACKEND_DIR / "data" / "raw"
OUT_CSV = BACKEND_DIR / "data" / "reference_prices.csv"

# ---------------------------------------------------------------- settings
MAX_FFILL_DAYS = 3          # forward-fill gaps of at most 3 days
MIN_MONTHS = 12             # drop commodities with less than 12 months of data
OUTLIER_RATIO = 3.0         # a month more than 3x (or less than 1/3) of its neighbours' median = typo
WPI_SOURCE = "wpi_derived"

# name shown in the app -> (row name in the WPI file, unit, ANCHOR price in Rs per unit)
# ANCHOR_PRICE = ASSUMED wholesale price of the last WPI month. Replace with real
# Agmarknet / mandi prices if you have them - nothing else needs to change.
COMMODITIES = {
    "Rice":         ("Rice, Non-basmati",  "kg",     40),
    "Wheat Atta":   ("Wheat flour (Atta)", "kg",     34),
    "Sugar":        ("Sugar",              "kg",     42),
    "Toor Dal":     ("Arhar",              "kg",    125),
    "Chana":        ("Gram",               "kg",     75),
    "Moong Dal":    ("Moong",              "kg",    110),
    "Onion":        ("Onion",              "kg",     28),
    "Potato":       ("Potato",             "kg",     22),
    "Tomato":       ("Tomato",             "kg",     30),
    "Milk":         ("Milk",               "litre",  50),
    "Soyabean Oil": ("Soyabean Oil",       "litre", 125),
    "Mustard Oil":  ("Mustard Oil",        "litre", 150),
    "Salt":         ("Salt",               "packet", 22),   # 1 kg packet
    "Tea":          ("Processed Tea",      "packet", 130),  # 250 g packet
}

# Commodities that are NOT in the WPI file -> fully synthetic (name: (unit, base price))
SYNTHETIC_ONLY = {
    "Paneer": ("kg", 330),
}


# ================================================================ step 1: read
def find_wpi_file() -> Path:
    files = sorted(RAW_DIR.rglob("WPI*.csv"))
    if not files:
        raise FileNotFoundError(f"No WPI*.csv found under {RAW_DIR}. Unzip the WPI dataset there.")
    return files[0]


def load_wpi(path: Path) -> pd.DataFrame:
    """Read the WPI csv. The file has an en-dash byte, so utf-8 fails -> fall back to cp1252."""
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp1252")

    df.columns = [c.strip() for c in df.columns]
    df["COMMODITIES"] = df["COMMODITIES"].astype(str).str.strip()

    # remove exact duplicate rows, and repeated commodity names (keep the first)
    before = len(df)
    df = df.drop_duplicates().drop_duplicates(subset="COMMODITIES", keep="first")
    print(f"[clean] duplicate rows removed: {before - len(df)}")

    # strip thousands-commas and convert every month column to a number
    month_cols = [c for c in df.columns if re.fullmatch(r"[A-Za-z]{3}-\d{2}", c)]
    for c in month_cols:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce")
    return df


def monthly_series(df: pd.DataFrame, wpi_name: str) -> pd.Series:
    """One commodity row -> Series indexed by the 15th of each month."""
    row = df[df["COMMODITIES"] == wpi_name]
    if row.empty:
        raise KeyError(f"'{wpi_name}' not found in WPI file")
    row = row.iloc[0]
    month_cols = [c for c in df.columns if re.fullmatch(r"[A-Za-z]{3}-\d{2}", c)]
    dates = pd.to_datetime(month_cols, format="%b-%y") + pd.Timedelta(days=14)  # 1st -> 15th
    return pd.Series(row[month_cols].to_numpy(dtype=float), index=dates, name=wpi_name)


# ================================================================ step 2: clean
def remove_typo_outliers(s: pd.Series) -> tuple[pd.Series, int]:
    """
    A value that is more than OUTLIER_RATIO (3x) above, or below 1/3 of, the median of its
    5 nearest months is treated as a typing error (e.g. 3250 typed instead of 325) and set to
    NaN; interpolation re-fills it later.
    Why a median? One bad value cannot drag a median, but it would drag a mean.
    Why 3x and not less? Vegetables like tomato really do jump 2x in a month (real monsoon
    spikes), and those must be KEPT. Only impossible jumps are typos.
    """
    med = s.rolling(5, center=True, min_periods=3).median()
    ratio = s / med
    bad = (ratio > OUTLIER_RATIO) | (ratio < 1 / OUTLIER_RATIO)
    return s.mask(bad), int(bad.sum())


def monthly_to_daily(s: pd.Series) -> pd.Series:
    """Monthly points (15th of month) -> a value for every calendar day."""
    s = s.dropna()
    days = pd.date_range(s.index.min(), s.index.max(), freq="D")
    daily = s.reindex(days)
    # bridge at most ONE missing month (~62 days); longer holes stay empty
    daily = daily.interpolate(method="time", limit=62, limit_area="inside")
    # the required rule: forward-fill small gaps (<= 3 days)
    daily = daily.ffill(limit=MAX_FFILL_DAYS)
    return daily.dropna()


def add_daily_detail(daily: pd.Series, name: str) -> pd.Series:
    """Tiny weekly wobble + daily noise so a straight interpolated line looks like real daily data."""
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    wobble = 1 + 0.004 * np.sin(2 * np.pi * daily.index.dayofweek.to_numpy() / 7)
    noise = np.exp(rng.normal(0, 0.006, len(daily)))
    return daily * wobble * noise


# ================================================================ step 3: build
def build_commodity_frame(df, name, wpi_name, unit, anchor, shift_years) -> pd.DataFrame | None:
    s = monthly_series(df, wpi_name)
    s, n_bad = remove_typo_outliers(s)
    if s.dropna().empty:
        print(f"[skip] {name}: no data")
        return None

    # shift whole years (done on the 15th-of-month dates, so no 29-Feb problems)
    s.index = s.index + pd.DateOffset(years=shift_years)

    daily_index = monthly_to_daily(s)
    last_real_index = s.dropna().iloc[-1]                     # index value of the last month
    daily_index = add_daily_detail(daily_index, name)

    wholesale = anchor * daily_index / last_real_index        # INDEX -> RUPEES
    rng = np.random.default_rng(zlib.crc32((name + "retail").encode()))
    markup = np.clip(rng.uniform(1.10, 1.15) + rng.normal(0, 0.004, len(wholesale)), 1.10, 1.15)
    retail = wholesale * markup

    out = pd.DataFrame(
        {
            "commodity": name,
            "market": MARKET_NAME,
            "price_date": wholesale.index,
            "wholesale_price": wholesale.round(2).to_numpy(),
            "retail_price": retail.round(2).to_numpy(),
            "unit": unit,
            "source": WPI_SOURCE,
        }
    )
    print(f"[ok]   {name:<13} outliers removed: {n_bad}")
    return out


def extend_to_date(frame: pd.DataFrame, end: date) -> pd.DataFrame:
    """Fill the gap between the last real day and `end` with the synthetic generator."""
    last_day = frame["price_date"].max().date()
    if last_day >= end:
        return frame
    last_price = float(frame.loc[frame["price_date"] == frame["price_date"].max(), "wholesale_price"].iloc[0])
    tail = generate_commodity(
        commodity=frame["commodity"].iloc[0],
        unit=frame["unit"].iloc[0],
        base_price=last_price,
        start=last_day + pd.Timedelta(days=1),
        end=end,
        seed=zlib.crc32(("tail" + frame["commodity"].iloc[0]).encode()),
    )
    return pd.concat([frame, tail], ignore_index=True)


def drop_short_series(all_df: pd.DataFrame) -> pd.DataFrame:
    """Drop commodities with less than MIN_MONTHS months (365 days) of history."""
    keep = []
    for name, g in all_df.groupby("commodity"):
        span_days = (g["price_date"].max() - g["price_date"].min()).days
        if span_days < MIN_MONTHS * 30:
            print(f"[drop] {name}: only {span_days} days of data")
        else:
            keep.append(g)
    return pd.concat(keep, ignore_index=True)


def print_summary(df: pd.DataFrame) -> None:
    g = df.groupby("commodity").agg(
        rows=("price_date", "size"),
        first_date=("price_date", "min"),
        last_date=("price_date", "max"),
        sources=("source", lambda x: "+".join(sorted(set(x)))),
    )
    g["first_date"] = g["first_date"].dt.strftime("%Y-%m-%d")
    g["last_date"] = g["last_date"].dt.strftime("%Y-%m-%d")
    print("\n=== reference_prices.csv summary ===")
    print(g.to_string())
    print(f"\nTotal rows: {len(df)}   commodities: {df['commodity'].nunique()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shift-years", type=int, default=None,
                        help="shift real dates forward by N years (default: auto, so data ends near today)")
    parser.add_argument("--no-extend", action="store_true",
                        help="do not extend the series to today with synthetic data")
    args = parser.parse_args()

    today = date.today()
    wpi_path = find_wpi_file()
    print(f"Reading {wpi_path}")
    df = load_wpi(wpi_path)

    # last month in the file -> auto shift so the series ends within a year of today
    month_cols = [c for c in df.columns if re.fullmatch(r"[A-Za-z]{3}-\d{2}", c)]
    last_file_date = pd.to_datetime(month_cols[-1], format="%b-%y").date()
    shift_years = args.shift_years if args.shift_years is not None else (today - last_file_date).days // 365
    print(f"Date shift: +{shift_years} years (file ends {last_file_date}, today is {today})")

    frames = []
    for name, (wpi_name, unit, anchor) in COMMODITIES.items():
        f = build_commodity_frame(df, name, wpi_name, unit, anchor, shift_years)
        if f is not None:
            if not args.no_extend:
                f = extend_to_date(f, today)
            frames.append(f)

    # commodities missing from the real data -> synthetic, covering the same period
    all_real = pd.concat(frames, ignore_index=True)
    start = all_real["price_date"].min().date()
    end = all_real["price_date"].max().date()
    for name, (unit, base) in SYNTHETIC_ONLY.items():
        frames.append(generate_commodity(name, unit, base, start, end))
        print(f"[synthetic] {name}: not in WPI, generated {start} -> {end}")

    out = pd.concat(frames, ignore_index=True)
    out = drop_short_series(out)
    out = out.sort_values(["commodity", "price_date"]).reset_index(drop=True)

    print_summary(out)
    out["price_date"] = out["price_date"].dt.strftime("%Y-%m-%d")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved -> {OUT_CSV}")


if __name__ == "__main__":
    main()
