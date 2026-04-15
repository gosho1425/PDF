"""
Application configuration.
Loaded from environment variables / .env file.
The Anthropic API key lives here ONLY — never sent to the frontend.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App metadata ───────────────────────────────────────────────────────────
    APP_NAME: str = "PaperLens"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ── LLM provider configuration ─────────────────────────────────────────────
    # SECURITY: API keys are backend-only. Never expose to frontend.
    #
    # Supported providers: "anthropic" | "openai" | "gemini"
    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL: str = "claude-sonnet-4-5"
    LLM_MAX_TOKENS: int = 8192
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT_SECONDS: int = 120

    # Provider API keys (set only the one you use)
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # ── Local storage ─────────────────────────────────────────────────────────
    # All data lives under DATA_DIR — never inside the Python package.
    DATA_DIR: Path = Path("data")

    @property
    def DB_PATH(self) -> Path:
        return self.DATA_DIR / "app.db"

    @property
    def SUMMARIES_DIR(self) -> Path:
        return self.DATA_DIR / "summaries"

    @property
    def EXTRACTIONS_DIR(self) -> Path:
        return self.DATA_DIR / "extractions"

    def ensure_dirs(self) -> None:
        """Create required data directories on startup."""
        self.SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
        self.EXTRACTIONS_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
