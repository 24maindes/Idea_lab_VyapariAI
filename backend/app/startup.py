"""
startup.py - things done once when the server starts.

ensure_reference_data(): if the reference_prices table is EMPTY, load data/reference_prices.csv into it.
So a fresh deployment (new empty PostgreSQL) has market prices without running any script by hand.
It is safe to run on every start: with data present it does nothing.
"""
import logging
from pathlib import Path

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import ReferencePrice

log = logging.getLogger("vyapari.startup")
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "reference_prices.csv"


def ensure_reference_data() -> int:
    """Returns the number of rows loaded (0 when nothing was needed or the CSV does not exist)."""
    db = SessionLocal()
    try:
        if db.execute(select(func.count()).select_from(ReferencePrice)).scalar():
            return 0
    finally:
        db.close()
    if not CSV_PATH.exists():
        log.warning("reference_prices is empty and %s does not exist. Run: python -m app.ml.build_reference", CSV_PATH)
        return 0
    from app.ml.load_reference import load           # same idempotent loader as the command line script
    inserted, _ = load()
    log.info("Loaded %s reference price rows at start-up", inserted)
    return inserted
