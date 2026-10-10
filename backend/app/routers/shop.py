"""
routers/shop.py - the shopkeeper's shop profile and business settings.

POST /api/shop   create the shop (once per user)
GET  /api/shop   read it
PUT  /api/shop   update it (send only the fields that changed)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.routers.auth import get_current_user
from app.database import get_db
from app.deps import get_current_shop
from app.models import Shop
from app.schemas import ShopCreate, ShopOut, ShopUpdate
from app.services.cache import invalidate_shop

router = APIRouter(prefix="/api/shop", tags=["shop"])

# columns that may be cleared by sending null; every other column ignores null
NULLABLE_FIELDS = {"shop_type", "location"}


@router.post("", response_model=ShopOut, status_code=201)
def create_shop(payload: ShopCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """One shop per user. A second POST is a 409 conflict (user_id is also UNIQUE in the database)."""
    exists = db.execute(select(Shop.id).where(Shop.user_id == user.id)).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=409, detail="You already have a shop. Use PUT /api/shop to change it.")
    shop = Shop(user_id=user.id, **payload.model_dump())     # user_id comes from the token, never from the request
    db.add(shop)
    db.commit()
    db.refresh(shop)
    invalidate_shop(shop.id)                                  # lead time, cover days, margins ... change the advice
    return shop


@router.get("", response_model=ShopOut)
def read_shop(shop: Shop = Depends(get_current_shop)):
    return shop


@router.put("", response_model=ShopOut)
def update_shop(payload: ShopUpdate, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    changes = payload.model_dump(exclude_unset=True)         # only fields the client really sent
    for field, value in changes.items():
        if value is None and field not in NULLABLE_FIELDS:
            continue
        setattr(shop, field, value)

    # the rule "min margin <= target margin" must also hold after a PARTIAL update
    if shop.min_margin_pct > shop.target_margin_pct:
        db.rollback()
        raise HTTPException(status_code=422, detail="minMarginPct cannot be higher than targetMarginPct")

    db.commit()
    db.refresh(shop)
    invalidate_shop(shop.id)                                  # lead time, cover days, margins ... change the advice
    return shop
