"""
services/activity.py - one tiny helper that writes a line to the activity log
(shown as "Recent activity" on the dashboard).
It only ADDS the row to the session; the caller commits, so the log entry and the
real change are saved together in ONE transaction.
"""
from sqlalchemy.orm import Session

from app.models import ActivityLog


def log_activity(db: Session, shop_id: int, kind: str, text: str) -> None:
    db.add(ActivityLog(shop_id=shop_id, kind=kind, text=text))
