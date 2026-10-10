"""
routers/recommendations.py - purchase recommendations (Buy Now / Buy Limited / Wait).

GET /api/recommendations/purchase                 all products, most urgent first
GET /api/recommendations/purchase/{productId}     one product
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import Shop
from app.services.cache import get_or_set
from app.services.common import get_shop_product
from app.services.decision_engine import recommend_all, recommend_for_product

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/purchase")
def purchase_recommendations(db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    return get_or_set(shop.id, "recommendations-all", 60, lambda: recommend_all(db, shop))     # cleared by every write of this shop


@router.get("/purchase/{product_id}")
def purchase_recommendation(product_id: int, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    return recommend_for_product(db, shop, get_shop_product(db, shop.id, product_id))


# ---------------------------------------------------------------- selling price
from fastapi import Query                                                   # noqa: E402
from app.services.pricing_engine import recommend_selling_price, recommend_selling_prices   # noqa: E402


@router.get("/selling-price")
def selling_prices(target_margin_pct: float | None = Query(None, alias="targetMarginPct", ge=0, le=100),
                   db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    return recommend_selling_prices(db, shop, target_margin_pct)


@router.get("/selling-price/{product_id}")
def selling_price(product_id: int, target_margin_pct: float | None = Query(None, alias="targetMarginPct", ge=0, le=100),
                  db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    return recommend_selling_price(db, shop, get_shop_product(db, shop.id, product_id), target_margin_pct)
