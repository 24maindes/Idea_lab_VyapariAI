"""
make_synthetic_reference.py
---------------------------
Generates SYNTHETIC daily wholesale/retail prices for ONE commodity.

When it is used (and only then):
  1. A commodity that does not exist in the real WPI file (e.g. Paneer).
  2. The short tail between the last real WPI month (shifted forward) and today,
     so the demo shop always has reference prices for "today".

Price model (easy to explain in a viva):

    wholesale(t) = base_price
                   x trend(t)        steady yearly inflation, e.g. +4 % per year
                   x seasonality(t)  smooth yearly wave (one up/down cycle per year)
                   x weekly(t)       tiny day-of-week wobble (mandi arrivals differ by day)
                   x shocks(t)       rare random jumps that fade away slowly (weather, strikes)
                   x noise(t)        small daily random noise

    retail(t) = wholesale(t) x markup    where markup is between 1.10 and 1.15

Everything is seeded, so running it twice gives identical numbers.
"""
import zlib
from datetime import date

import numpy as np
import pandas as pd

MARKET_NAME = "All India"
SOURCE_NAME = "synthetic"


def _seed_from_name(name: str) -> int:
    """Stable seed from a commodity name (Python's hash() changes every run, crc32 does not)."""
    return zlib.crc32(name.encode("utf-8"))


def generate_commodity(
    commodity: str,
    unit: str,
    base_price: float,
    start: date,
    end: date,
    seed: int | None = None,
    trend_pct_per_year: float = 4.0,
    season_amplitude: float = 0.06,
    weekly_amplitude: float = 0.006,
    shock_probability: float = 0.01,
    shock_size: float = 0.06,
    noise_sd: float = 0.005,
) -> pd.DataFrame:
    """
    Return a DataFrame with the reference_prices columns:
    commodity, market, price_date, wholesale_price, retail_price, unit, source

    base_price = wholesale price (Rs per unit) on the `start` date.
    """
    if end < start:
        raise ValueError("end date must not be before start date")

    rng = np.random.default_rng(_seed_from_name(commodity) if seed is None else seed)
    days = pd.date_range(start, end, freq="D")
    n = len(days)
    t = np.arange(n)

    # 1) trend: compound yearly growth
    trend = (1 + trend_pct_per_year / 100) ** (t / 365.0)

    # 2) yearly seasonality: sine wave with a random phase, divided by its value at t=0
    #    so the first day is exactly base_price.
    phase = rng.uniform(0, 2 * np.pi)
    doy = days.dayofyear.to_numpy()
    season = 1 + season_amplitude * np.sin(2 * np.pi * doy / 365.25 + phase)
    season = season / season[0]

    # 3) weekly wobble
    weekly = 1 + weekly_amplitude * np.sin(2 * np.pi * days.dayofweek.to_numpy() / 7)

    # 4) random shocks that decay (each day keeps 97 % of yesterday's shock)
    shock_events = np.where(rng.random(n) < shock_probability, rng.normal(0, shock_size, n), 0.0)
    level = np.zeros(n)
    for i in range(1, n):
        level[i] = level[i - 1] * 0.97 + shock_events[i]
    shocks = np.exp(level)

    # 5) daily noise
    noise = np.exp(rng.normal(0, noise_sd, n))

    wholesale = base_price * trend * season * weekly * shocks * noise

    # retail = wholesale x (1.10 .. 1.15). One markup per commodity + tiny jitter, clipped to the range.
    base_markup = rng.uniform(1.10, 1.15)
    markup = np.clip(base_markup + rng.normal(0, 0.004, n), 1.10, 1.15)
    retail = wholesale * markup

    return pd.DataFrame(
        {
            "commodity": commodity,
            "market": MARKET_NAME,
            "price_date": days,
            "wholesale_price": np.round(wholesale, 2),
            "retail_price": np.round(retail, 2),
            "unit": unit,
            "source": SOURCE_NAME,
        }
    )


if __name__ == "__main__":
    # Quick demo:  python -m app.ml.make_synthetic_reference
    demo = generate_commodity("Paneer", "kg", 330, date(2025, 1, 1), date(2025, 12, 31))
    print(demo.head())
    print(demo.wholesale_price.describe())
