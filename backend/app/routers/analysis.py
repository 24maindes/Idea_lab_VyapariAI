"""
routers/analysis.py
-------------------
Fair-price analysis API. Every endpoint is protected and scoped to the logged-in user's shop.

GET /api/analysis/fair-price                          one summary row per product
GET /api/analysis/fair-price/check?productId=&price=&date=   quick "is this price fair?" check
GET /api/analysis/fair-price/{productId}?days=180     full detail for one product

IMPORTANT: /check is declared BEFORE /{productId}. FastAPI matches routes top to bottom,
so otherwise the word "check" would be read as a product id and fail with a 422.
"""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.routers.auth import get_current_user
from app.database import get_db
from app.models import Product, Shop
from app.schemas import CamelModel
from app.services.fair_price import (check_message, get_reference_price, product_fair_price,
                                     variance_pct, verdict)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


# ------------------------------------------------------------------ response schemas
class SeriesPoint(CamelModel):
    date: dt.date
    reference_price: float


class PurchasePoint(CamelModel):
    date: dt.date
    price: float
    supplier: str
    supplier_id: int | None = None
    quantity: float
    variance_pct: float | None = None


class SupplierVariance(CamelModel):
    supplier_id: int | None = None
    supplier: str
    avg_variance_pct: float
    purchases: int
    total_quantity: float


class FairPriceSummary(CamelModel):
    product_id: int
    product_name: str
    unit: str | None = None
    category: str | None = None
    reference_commodity: str | None = None
    has_market_data: bool
    last_purchase_date: dt.date | None = None
    last_purchase_price: float | None = None
    reference_price: float | None = None
    variance_pct: float | None = None
    verdict: str | None = None
    potential_savings: float = 0.0


class FairPriceDetail(FairPriceSummary):
    avg30_day_price: float | None = None          # JSON key: avg30DayPrice
    overspend90_days: float = 0.0                 # JSON key: overspend90Days
    days: int
    series: list[SeriesPoint] = []
    points: list[PurchasePoint] = []
    supplier_breakdown: list[SupplierVariance] = []


class FairPriceCheck(CamelModel):
    has_market_data: bool
    reference_price: float | None = None
    variance_pct: float | None = None
    verdict: str | None = None
    message: str


# ------------------------------------------------------------------ helpers
def get_user_shop(db: Session, user) -> Shop:
    """The shop that belongs to the logged-in user (column may be user_id or owner_id)."""
    owner_col = "user_id" if hasattr(Shop, "user_id") else "owner_id"
    shop = db.execute(select(Shop).where(getattr(Shop, owner_col) == user.id)).scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=404, detail="Shop not found for this user")
    return shop


def get_shop_product(db: Session, shop: Shop, product_id: int) -> Product:
    """A product, but ONLY if it belongs to this shop. Other shops' ids look like 'not found'."""
    product = db.execute(
        select(Product).where(Product.id == product_id, Product.shop_id == shop.id)
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ------------------------------------------------------------------ endpoints
@router.get("/fair-price", response_model=list[FairPriceSummary])
def fair_price_summary(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """One row per product of the shop (used for the table and the product dropdown)."""
    shop = get_user_shop(db, user)
    products = db.execute(select(Product).where(Product.shop_id == shop.id).order_by(Product.name)).scalars().all()
    return [product_fair_price(db, shop, p) for p in products]


# NOTE: declared before /{product_id}
@router.get("/fair-price/check", response_model=FairPriceCheck)
def fair_price_check(
    product_id: int = Query(..., alias="productId"),
    price: float = Query(..., gt=0, description="price per unit in Rs"),
    on_date: dt.date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Is this price fair? Used live by the purchase form. No market data is a normal answer, not an error."""
    shop = get_user_shop(db, user)
    product = get_shop_product(db, shop, product_id)
    today = dt.date.today()
    on_date = on_date or today

    ref = get_reference_price(db, getattr(product, "reference_commodity", None), on_date)
    if ref is None:
        return FairPriceCheck(has_market_data=False, message="No market price available for this product on that date")

    var = variance_pct(price, ref)
    return FairPriceCheck(
        has_market_data=True, reference_price=round(ref, 2), variance_pct=var,
        verdict=verdict(var), message=check_message(price, ref, var, on_date, today),
    )


@router.get("/fair-price/{product_id}", response_model=FairPriceDetail)
def fair_price_detail(
    product_id: int,
    days: int = Query(180, ge=7, le=730),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Full detail for one product: stats, reference line, purchase dots, supplier comparison."""
    shop = get_user_shop(db, user)
    product = get_shop_product(db, shop, product_id)
    return product_fair_price(db, shop, product, days=days)
