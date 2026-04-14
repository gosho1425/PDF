"""Job tracking schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ProcessingJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paper_id: Optional[uuid.UUID] = None
    celery_task_id: Optional[str] = None
    job_type: str
    status: str
    progress_percent: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
