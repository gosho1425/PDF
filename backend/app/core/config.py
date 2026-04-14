"""
Application configuration loaded exclusively from environment variables.
Never hardcode secrets here.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "PaperLens"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── API ────────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Database ───────────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "paperlens"
    POSTGRES_USER: str = "paperlens"
    POSTGRES_PASSWORD: str = ""  # Must be set in .env

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Redis / Celery ─────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL

    # ── LLM – Claude (Anthropic) ───────────────────────────────────────────────
    # CRITICAL: This key is NEVER exposed to the frontend.
    # All LLM calls are made server-side only.
    ANTHROPIC_API_KEY: str = ""  # Must be set in .env
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_MAX_TOKENS: int = 8192
    ANTHROPIC_TEMPERATURE: float = 0.1  # Low temp for factual extraction
    LLM_MAX_CHUNK_CHARS: int = 60000   # ~15k tokens per chunk
    LLM_TIMEOUT_SECONDS: int = 120

    # ── File Storage ───────────────────────────────────────────────────────────
    # Abstracted so it can be swapped for S3 later.
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    DATA_DIR: Path = Path("/app/data")

    # S3 settings (only used when STORAGE_BACKEND="s3")
    S3_BUCKET: Optional[str] = None
    S3_REGION: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    @property
    def PAPERS_DIR(self) -> Path:
        return self.DATA_DIR / "papers"

    @property
    def EXPORTS_DIR(self) -> Path:
        return self.DATA_DIR / "exports"

    # ── PDF Processing ─────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    OCR_ENABLED: bool = True          # Fall back to OCR when native text < threshold
    OCR_MIN_TEXT_THRESHOLD: int = 200  # chars; below this triggers OCR fallback
    TESSERACT_CMD: Optional[str] = None  # Override path to tesseract binary

    # ── Extraction Schema ──────────────────────────────────────────────────────
    SCHEMA_VERSION: str = "1.0.0"

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" | "console"

    def ensure_dirs(self) -> None:
        """Create required data directories if they don't exist."""
        self.PAPERS_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
