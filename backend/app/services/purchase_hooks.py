"""
services/purchase_hooks.py - things that happen AFTER a purchase is saved.
The result is sent back to the browser as "insights" (e.g. {"anomaly": {...}}).
"""
from sqlalchemy.orm import Session

from app.models import Purchase
from app.services.anomaly_service import check_purchase


def after_purchase(db: Session, purchase: Purchase) -> dict:
    insights: dict = {}
    try:
        anomaly = check_purchase(db, purchase)           # None when the price looks normal
        if anomaly:
            insights["anomaly"] = anomaly
    except Exception:                                    # a failed check must NEVER block saving a purchase
        pass
    return insights
