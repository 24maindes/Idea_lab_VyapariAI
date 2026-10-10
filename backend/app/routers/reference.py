"""
routers/reference.py
--------------------
Read-only API for the reference (market) prices.

GET /api/reference/commodities                     -> list of commodities
GET /api/reference/prices?commodity=&from=&to=&limit=  -> daily prices (oldest first)
GET /api/reference/latest?commodity=               -> most recent price row

Reference prices are PUBLIC market data shared by every shop (they have no shop_id),
so there is nothing to scope per shop. We still require a logged-in user.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.routers.auth import get_current_user
from app.database import get_db
from app.models import ReferencePrice
from app.schemas import CamelModel

router = APIRouter(prefix="/api/reference", tags=["reference"])


# ------------------------------------------------------------------ response schemas
class CommodityOut(CamelModel):
    name: str
    unit: str
    first_date: date
    last_date: date
    source: str          # "wpi_derived", "synthetic" or "synthetic, wpi_derived"


class ReferencePriceOut(CamelModel):
    commodity: str
    market: str
    price_date: date
    wholesale_price: float
    retail_price: float | None = None
    unit: str
    source: str


# ------------------------------------------------------------------ endpoints
@router.get("/commodities", response_model=list[CommodityOut])
def list_commodities(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """One row per commodity with its date range and data source(s)."""
    rows = db.execute(
        select(
            ReferencePrice.commodity,
            func.min(ReferencePrice.unit),
            func.min(ReferencePrice.price_date),
            func.max(ReferencePrice.price_date),
        )
        .group_by(ReferencePrice.commodity)
        .order_by(ReferencePrice.commodity)
    ).all()

    # distinct sources per commodity (a commodity can be real + synthetic tail)
    src_rows = db.execute(select(ReferencePrice.commodity, ReferencePrice.source).distinct()).all()
    sources: dict[str, set[str]] = {}
    for commodity, source in src_rows:
        sources.setdefault(commodity, set()).add(source)

    return [
        CommodityOut(
            name=name, unit=unit, first_date=first, last_date=last,
            source=", ".join(sorted(sources.get(name, []))),
        )
        for name, unit, first, last in rows
    ]


@router.get("/prices", response_model=list[ReferencePriceOut])
def get_prices(
    commodity: str = Query(..., description="exact commodity name, e.g. Rice"),
    date_from: date | None = Query(None, alias="from"),   # 'from' is a Python keyword, so we use an alias
    date_to: date | None = Query(None, alias="to"),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Daily prices, oldest first. If `limit` cuts the list we return the NEWEST `limit` rows
    (a chart normally wants the recent past), still sorted oldest -> newest.
    """
    q = select(ReferencePrice).where(ReferencePrice.commodity == commodity)
    if date_from:
        q = q.where(ReferencePrice.price_date >= date_from)
    if date_to:
        q = q.where(ReferencePrice.price_date <= date_to)

    rows = db.execute(q.order_by(ReferencePrice.price_date.desc()).limit(limit)).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No reference prices found for '{commodity}'")
    rows.reverse()
    return rows


@router.get("/latest", response_model=ReferencePriceOut)
def get_latest(
    commodity: str = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """The most recent price row for one commodity."""
    row = db.execute(
        select(ReferencePrice)
        .where(ReferencePrice.commodity == commodity)
        .order_by(ReferencePrice.price_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No reference prices found for '{commodity}'")
    return row
