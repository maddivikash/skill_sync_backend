import os
from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./skillsync.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallbacksecret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    # Log SQL only in dev. Noisy + leaks data in prod/CloudWatch otherwise.
    SQL_ECHO: bool = _as_bool(os.getenv("SQL_ECHO", "false"))

    # Dev convenience: create tables on startup. In prod use Alembic migrations.
    AUTO_CREATE_TABLES: bool = _as_bool(os.getenv("AUTO_CREATE_TABLES", "false"))

    # Comma-separated list of allowed CORS origins for the frontend.
    CORS_ORIGINS: list = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
        ).split(",")
        if o.strip()
    ]

    # Where the frontend lives — used to build password-reset links.
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", 30))

    # Email (SMTP). If unset, the app runs in "dev mode" and logs reset links
    # instead of emailing them — works with zero setup / zero cost.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "Ascend <no-reply@ascenddaily.in>")

    # AI coach (Groq — free hosted LLM API). If unset, the chat endpoint is off.
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    # One or more keys (comma-separated) — rotated on rate limits for failover.
    GROQ_API_KEYS: list = [
        k.strip()
        for k in os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", "")).split(",")
        if k.strip()
    ]
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


settings = Settings()
