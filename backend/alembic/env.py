"""
Alembic migration environment.
Loads database URL from environment variables (never hardcoded).
"""
from __future__ import annotations

import os
import sys
import time
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.db.base import Base

# Import ALL models so Alembic can detect them
from app.models import (  # noqa: F401
    Paper, Author, PaperAuthor, Journal,
    ExtractionRecord, MaterialEntity, ProcessCondition,
    MeasurementMethod, ResultProperty, SourceEvidence,
    ProcessingJob,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

log = logging.getLogger("alembic.env")


def get_url() -> str:
    """Return a properly URL-encoded database connection string."""
    return get_settings().DATABASE_URL


def wait_for_db(url: str, retries: int = 30, delay: float = 2.0) -> None:
    """
    Block until the database accepts a real connection (not just a TCP ping).
    This is needed because pg_isready returns OK once the socket is open, but
    PostgreSQL may still be initialising auth / roles for a few more seconds.

    Raises RuntimeError after *retries* failed attempts.
    """
    from sqlalchemy import create_engine

    for attempt in range(1, retries + 1):
        try:
            engine = create_engine(url, poolclass=pool.NullPool)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            log.info(f"[wait_for_db] Database is ready (attempt {attempt}/{retries})")
            return
        except Exception as exc:
            log.warning(
                f"[wait_for_db] Attempt {attempt}/{retries} failed: {exc!r}. "
                f"Retrying in {delay}s…"
            )
            time.sleep(delay)

    raise RuntimeError(
        f"Database did not become available after {retries} attempts. "
        "Check POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD in your .env."
    )


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()

    # Wait for the database to be genuinely ready before attempting migrations.
    # This guards against the race condition where pg_isready passes but
    # Postgres hasn't finished initialising roles / auth on first boot.
    wait_for_db(url)

    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
