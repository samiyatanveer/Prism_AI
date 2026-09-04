"""
PrismAI Backend — Application Configuration

All settings are loaded from environment variables. No secrets are
hardcoded. Pydantic-settings validates types and provides clear errors
when required variables are missing.
"""

import base64
from functools import lru_cache
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Resolve relative to the backend package so launching Uvicorn from
        # the repository root still loads backend/.env.
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_env: str = "development"
    app_name: str = "PrismAI"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────────────────
    database_url: str  # required — no default

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT / Auth ───────────────────────────────────────────
    secret_key: str  # required — no default
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Encryption (exchange credential storage) ─────────────
    encryption_key: str  # required — no default; 32-byte base64-encoded AES key

    # ── AI / Groq ─────────────────────────────────────────────
    # groq_api_key is required only when the AI assistant is used.
    # Default is empty string so the app starts without it.
    # NEVER log, return, or include this key in any response or prompt.
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_timeout: float = 30.0  # seconds per LLM call

    allowed_origins: list[str] = ["http://localhost:3000"]
    # ── Binance ─────────────────────────────────────────────────
    binance_base_url: str = "https://api.binance.com"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, value: str) -> str:
        """Fail at startup rather than when the first exchange is connected."""
        try:
            decoded = base64.b64decode(value, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("ENCRYPTION_KEY must be valid base64-encoded data.") from exc
        if len(decoded) != 32:
            raise ValueError("ENCRYPTION_KEY must decode to exactly 32 bytes.")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings. Call this instead of instantiating Settings directly."""
    return Settings()
