"""
routers/forecast.py - price forecasts for the shop's products.

GET  /api/forecast/{productId}?horizon=7|14     forecast for a product's linked commodity
GET  /api/forecast/models?commodity=            model comparison table (MAPE / RMSE)
POST /api/forecast/retrain?commodity=           retrain in the background (one job at a time)
GET  /api/forecast/retrain/status               state of the retrain job

Fixed routes (/models, /retrain...) are declared BEFORE /{productId}.
"""
import datetime as dt
import threading
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.deps import get_current_shop
from app.models import ModelMetric, ReferencePrice, Shop
from app.routers.auth import get_current_user
from app.services.common import get_shop_product
from app.services.forecast_service import NoModelError, forecast_for_commodity, invalidate_forecasts

router = APIRouter(prefix="/api/forecast", tags=["forecast"])

_job_lock = threading.Lock()
_job = {"state": "idle", "commodity": None, "startedAt": None, "finishedAt": None, "message": None, "trained": 0, "skipped": [], "failed": []}


def _run_retrain(commodity: str | None) -> None:
    """Runs in a background thread. Never raises: the outcome is stored in _job."""
    from app.ml import train_forecast
    try:
        results = train_forecast.main(commodity, verbose=False)
        skipped = [r for r in results if "skipped" in r]
        failed = [r for r in results if "error" in r]
        trained = len(results) - len(skipped) - len(failed)
        invalidate_forecasts(commodity)                       # users immediately see forecasts from the new models
        msg = f"Trained {trained} commodit{'y' if trained == 1 else 'ies'}"
        if skipped:
            msg += "; skipped: " + ", ".join(f"{r['commodity']} ({r['skipped']})" for r in skipped)
        if failed:
            msg += "; failed (old model kept): " + ", ".join(f"{r['commodity']} ({r['error']})" for r in failed)
        if not trained:
            msg = "Nothing was trained. " + msg
        _job.update(state="done" if trained else "error", message=msg, trained=trained,
                    skipped=[{"commodity": r["commodity"], "reason": r["skipped"]} for r in skipped],
                    failed=[{"commodity": r["commodity"], "error": r["error"]} for r in failed])
    except SystemExit as e:
        _job.update(state="error", message=str(e))
    except Exception as e:
        _job.update(state="error", message=f"Retraining failed: {e}")
    finally:
        _job["finishedAt"] = dt.datetime.now().isoformat(timespec="seconds")


@router.get("/models")
def model_table(commodity: str | None = Query(None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = select(ModelMetric).order_by(ModelMetric.commodity, ModelMetric.mape)
    if commodity:
        q = q.where(ModelMetric.commodity == commodity)
    return [{"commodity": m.commodity, "modelName": m.model_name, "mape": m.mape, "rmse": m.rmse, "isBest": bool(m.is_best),
             "trainedAt": m.trained_at.isoformat() if m.trained_at else None} for m in db.execute(q).scalars()]


@router.post("/retrain", status_code=202)
def retrain(background: BackgroundTasks, commodity: str | None = Query(None), db: Session = Depends(get_db),
            user=Depends(get_current_user)):
    if commodity and db.execute(select(ReferencePrice.id).where(ReferencePrice.commodity == commodity).limit(1)).first() is None:
        raise HTTPException(status_code=404, detail=f"Unknown commodity '{commodity}'")
    with _job_lock:                                   # only ONE retrain job at a time
        if _job["state"] == "running":
            raise HTTPException(status_code=409, detail="A retrain job is already running")
        _job.update(state="running", commodity=commodity, startedAt=dt.datetime.now().isoformat(timespec="seconds"),
                    finishedAt=None, message=None, trained=0, skipped=[], failed=[])
    background.add_task(_run_retrain, commodity)
    return dict(_job)


@router.get("/retrain/status")
def retrain_status(user=Depends(get_current_user)):
    return dict(_job)


@router.get("/{product_id}")
def product_forecast(product_id: int, horizon: int = Query(7), db: Session = Depends(get_db),
                     shop: Shop = Depends(get_current_shop)):
    if horizon not in (7, 14):
        raise HTTPException(status_code=422, detail="horizon must be 7 or 14")
    product = get_shop_product(db, shop.id, product_id)
    commodity = product.reference_commodity
    base = {"productId": product.id, "productName": product.name, "unit": product.unit}
    if not commodity:
        return {**base, "available": False, "reason": "This product is not linked to a market commodity. Link one on the Products page."}
    try:
        data = forecast_for_commodity(db, commodity, horizon)
    except NoModelError:
        return {**base, "available": False, "commodity": commodity,
                "reason": f"No trained forecast model for {commodity} yet. Use 'Retrain models' to create one."}
    return {**base, "available": True, **data}
