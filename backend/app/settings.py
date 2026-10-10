"""
settings.py - configuration that must be right in PRODUCTION. Everything comes from environment variables
(a local .env file is read for development; never commit it).

    ENV                    "development" (default) or "production"
    SECRET_KEY             signs login tokens. REQUIRED in production, at least 32 characters, random.
    DATABASE_URL           sqlite:///./vyapariai.db (default) or postgresql://user:password@host:5432/dbname
    CORS_ORIGINS           comma separated allowed browser origins, e.g. https://vyapariai.vercel.app
    GEMINI_API_KEY, GEMINI_MODEL   for the AI advisor (without them the advisor answers with the offline fallback)

check_production() stops the server at start-up with a clear message when something unsafe is configured.
"""
import os

from dotenv import load_dotenv

load_dotenv()

BAD_SECRETS = {"", "insecure_dev_secret", "change-me", "changeme", "secret", "change-me-to-a-long-random-string"}


def env() -> str:
    return os.getenv("ENV", "development").strip().lower()


def is_production() -> bool:
    return env() == "production"


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


def check_production() -> list[str]:
    """Raise RuntimeError when ENV=production and the configuration is unsafe. Returns warnings (also for development)."""
    problems, warnings = [], []
    secret = os.getenv("SECRET_KEY", "")
    if secret in BAD_SECRETS or len(secret) < 32:
        (problems if is_production() else warnings).append(
            "SECRET_KEY is missing, a placeholder or shorter than 32 characters. Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\"")
    origins = cors_origins()
    if is_production():
        if any("localhost" in o or "127.0.0.1" in o for o in origins):
            problems.append("CORS_ORIGINS still contains localhost. Set it to your real frontend address(es).")
        if "*" in origins:
            problems.append("CORS_ORIGINS must not be '*' (the app uses login tokens).")
        if os.getenv("DATABASE_URL", "").startswith("sqlite"):
            warnings.append("DATABASE_URL is SQLite. Use PostgreSQL in production (SQLite files are lost on many hosting services).")
        if not os.getenv("DATABASE_URL"):
            problems.append("DATABASE_URL is not set.")
    if problems:
        raise RuntimeError("Unsafe production configuration:\n - " + "\n - ".join(problems))
    return warnings
