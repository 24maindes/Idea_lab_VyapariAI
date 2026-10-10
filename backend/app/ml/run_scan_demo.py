"""
run_scan_demo.py - scan the demo shop and report how many of the injected anomalies were caught.

    python -m app.ml.run_scan_demo

(It first removes the demo shop's old alerts so the numbers always come from a fresh scan.)
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.models import Alert, Shop, User
from app.services.anomaly_service import scan_shop

GT = Path(__file__).resolve().parents[2] / "data" / "anomaly_ground_truth.csv"


def main() -> None:
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == "demo@vyapariai.com")).scalar_one_or_none()
        if user is None:
            raise SystemExit("Demo user not found. Run python -m app.ml.seed_demo first.")
        shop = db.execute(select(Shop).where(Shop.user_id == user.id)).scalar_one()
        db.execute(delete(Alert).where(Alert.shop_id == shop.id))
        db.commit()

        result = scan_shop(db, shop)
        flagged = set(db.execute(select(Alert.purchase_id).where(Alert.shop_id == shop.id, Alert.alert_type == "price_anomaly")).scalars())
        truth = set(pd.read_csv(GT)["purchase_id"])
        caught, false_alarms, missed = flagged & truth, flagged - truth, truth - flagged
        precision = len(caught) / len(flagged) if flagged else 0
        recall = len(caught) / len(truth) if truth else 0

        print(f"Alerts created: {result['created']}")
        print(f"Injected anomalies: {len(truth)} | caught: {len(caught)} | missed: {len(missed)} | false alarms: {len(false_alarms)}")
        print(f"Precision {precision:.2f}  Recall {recall:.2f}")
        again = scan_shop(db, shop)
        print(f"Second scan created {again['newAlerts']} new alerts (must be 0)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
