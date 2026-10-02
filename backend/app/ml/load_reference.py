"""
load_reference.py
-----------------
Loads backend/data/reference_prices.csv into the `reference_prices` table.

Run from the backend folder:
    python -m app.ml.load_reference

IDEMPOTENT: a row is identified by (commodity, market, price_date). Rows that are already
in the table are skipped, so you can run this script many times and never get duplicates.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import insert, select

from app.database import Base, SessionLocal, engine
from app.models import ReferencePrice

BACKEND_DIR = Path(__file__).resolve().parents[2]
CSV_PATH = BACKEND_DIR / "data" / "reference_prices.csv"
CHUNK = 5000   # insert in batches so SQLite/PostgreSQL never get one giant statement


def load() -> tuple[int, int]:
    """Returns (inserted, skipped)."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"{CSV_PATH} not found. Run: python -m app.ml.build_reference")

    df = pd.read_csv(CSV_PATH, parse_dates=["price_date"])
    df["price_date"] = df["price_date"].dt.date
    # empty retail price -> None (NULL in the database)
    df["retail_price"] = df["retail_price"].astype(object).where(df["retail_price"].notna(), None)

    Base.metadata.create_all(bind=engine)     # make sure the tables exist

    db = SessionLocal()
    try:
        # keys that are already stored
        existing = set(
            db.execute(select(ReferencePrice.commodity, ReferencePrice.market, ReferencePrice.price_date)).all()
        )
        records = df.to_dict(orient="records")
        new_rows = [r for r in records if (r["commodity"], r["market"], r["price_date"]) not in existing]

        for i in range(0, len(new_rows), CHUNK):
            db.execute(insert(ReferencePrice), new_rows[i:i + CHUNK])
        db.commit()
        return len(new_rows), len(records) - len(new_rows)
    finally:
        db.close()


if __name__ == "__main__":
    inserted, skipped = load()
    print(f"reference_prices: inserted {inserted} rows, skipped {skipped} (already present)")
