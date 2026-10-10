"""routers/activity.py - latest activity lines of the shop (newest first)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import ActivityLog, Shop
from app.schemas import ActivityOut

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("", response_model=list[ActivityOut])
def list_activity(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    return db.execute(
        select(ActivityLog).where(ActivityLog.shop_id == shop.id)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit)
    ).scalars().all()
