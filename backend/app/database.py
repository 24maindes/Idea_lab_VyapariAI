import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vyapariai.db")



def normalize_url(url: str) -> str:
    """Hosting services (Render, Heroku ...) give "postgres://..." but SQLAlchemy wants "postgresql://..."."""
    return "postgresql://" + url[len("postgres://"):] if url.startswith("postgres://") else url


DATABASE_URL = normalize_url(DATABASE_URL)

# check_same_thread only needed for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# pool_pre_ping: test a connection before using it, so a database that restarted does not cause an error on the first request
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=not DATABASE_URL.startswith("sqlite"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
