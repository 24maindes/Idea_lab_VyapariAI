from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401 - ensures models are registered before create_all
from app.routers import auth

# Creates vyapariai.db and the users table on first run
Base.metadata.create_all(bind=engine)

app = FastAPI(title="VyapariAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server default port
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "VyapariAI API"}
