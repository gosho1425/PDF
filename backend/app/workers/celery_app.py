"""
Celery application configuration.
Workers run in separate processes and communicate through Redis.
"""
from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()

    app = Celery(
        "paperlens",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.workers.tasks"],
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,  # process one task at a time (LLM is slow)
        task_soft_time_limit=600,      # 10 min soft limit
        task_time_limit=720,           # 12 min hard limit
        task_max_retries=3,
        task_default_retry_delay=30,
        # Rate limiting: don't hammer the LLM API
        task_annotations={
            "app.workers.tasks.extract_paper": {
                "rate_limit": "5/m",  # 5 extraction tasks per minute
            }
        },
        # Result expiry
        result_expires=86400,  # 24 hours
        # Routing
        task_routes={
            "app.workers.tasks.parse_pdf": {"queue": "parse"},
            "app.workers.tasks.extract_paper": {"queue": "extract"},
            "app.workers.tasks.run_full_pipeline": {"queue": "pipeline"},
            "app.workers.tasks.scan_folder": {"queue": "pipeline"},
        },
    )

    return app


celery_app = create_celery_app()
