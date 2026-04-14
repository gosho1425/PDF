"""Job status tracking API."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, desc

from app.core.logging import get_logger
from app.models.job import ProcessingJob
from app.workers.celery_app import celery_app

router = APIRouter()
log = get_logger(__name__)


@router.get("/{job_id}/celery-status")
async def get_celery_task_status(job_id: str):
    """Get real-time Celery task status."""
    result = celery_app.AsyncResult(job_id)
    return {
        "task_id": job_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "traceback": str(result.traceback) if result.failed() else None,
    }


@router.get("")
async def list_jobs(
    paper_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List processing jobs, optionally filtered by paper."""
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    with SyncSession() as db:
        query = select(ProcessingJob).order_by(desc(ProcessingJob.created_at))
        if paper_id:
            query = query.where(ProcessingJob.paper_id == paper_id)

        jobs = list(db.execute(query.offset(skip).limit(limit)).scalars().all())
        return {
            "items": [
                {
                    "id": str(j.id),
                    "paper_id": str(j.paper_id) if j.paper_id else None,
                    "celery_task_id": j.celery_task_id,
                    "job_type": j.job_type,
                    "status": j.status,
                    "progress_percent": j.progress_percent,
                    "retry_count": j.retry_count,
                    "error_message": j.error_message,
                    "created_at": j.created_at.isoformat(),
                    "updated_at": j.updated_at.isoformat(),
                }
                for j in jobs
            ]
        }
