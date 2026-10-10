"""
deps.py - shared FastAPI dependencies.

get_current_shop = "the shop of the logged-in user".
Every shop-scoped endpoint uses it, so the shop id always comes from the login token
and never from something the client sends. That is what keeps shops separated.
"""
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.routers.auth import get_current_user
from app.database import get_db
from app.models import Shop


def get_current_shop(db: Session = Depends(get_db), user=Depends(get_current_user)) -> Shop:
    shop = db.execute(select(Shop).where(Shop.user_id == user.id)).scalar_one_or_none()
    if shop is None:
        # 404 with a clear message; the frontend uses it to send new users to /shop-setup
        raise HTTPException(status_code=404, detail="Shop not set up yet")
    return shop
