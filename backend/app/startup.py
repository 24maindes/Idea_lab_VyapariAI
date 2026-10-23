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


def ensure_demo_data() -> None:
    """Seeds the demo shop and presentation data if no users exist in the database."""
    db = SessionLocal()
    try:
        from app.models import User
        if db.execute(select(func.count()).select_from(User)).scalar():
            return
    finally:
        db.close()

    try:
        from app.ml.seed_demo import main as seed_main
        seed_main()
        log.info("Auto-seeded demo shop data at start-up")
    except Exception as e:
        log.exception("Could not seed demo shop data at start-up: %s", e)

    try:
        from scripts.enrich_presentation_data import main as enrich_main
        enrich_main()
        log.info("Auto-enriched presentation data at start-up")
    except Exception as e:
        log.exception("Could not enrich presentation data at start-up: %s", e)

