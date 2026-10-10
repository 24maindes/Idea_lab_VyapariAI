import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import settings
from app.database import Base, engine
from app import models  # noqa: F401 - makes sure all 11 tables are registered before create_all
from app.routers import activity, advisor, analysis, anomalies, auth, dashboard, forecast, imports, inventory, products, purchases, recommendations, reference, sales, shop, suppliers

log = logging.getLogger("vyapari")

# Stops the server with a clear message when ENV=production and the configuration is unsafe
for warning in settings.check_production():
    log.warning("Configuration warning: %s", warning)

# Creates every table on first run (existing tables are left untouched)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        from app.startup import ensure_reference_data
        ensure_reference_data()                      # empty reference_prices -> load the CSV (idempotent)
        import threading
        from app.services.forecast_service import warm_up
        threading.Thread(target=warm_up, daemon=True).start()     # load the saved models in the background
    except Exception:                                # a start-up convenience must never stop the server
        log.exception("Could not load the reference prices at start-up")
    yield


app = FastAPI(title="VyapariAI API", lifespan=lifespan)

# Allowed browser origins come from the environment: CORS_ORIGINS="http://localhost:5173,https://myapp.com"
origins = settings.cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(shop.router)
app.include_router(reference.router)
app.include_router(analysis.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(purchases.router)
app.include_router(sales.router)
app.include_router(inventory.router)
app.include_router(activity.router)
app.include_router(forecast.router)
app.include_router(anomalies.router)
app.include_router(recommendations.router)
app.include_router(dashboard.router)
app.include_router(imports.router)
app.include_router(advisor.router)


@app.get("/api/health")
def health():
    """Public (no login) - used to check that the server is alive."""
    return {"status": "ok"}
