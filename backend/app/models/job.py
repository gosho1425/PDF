"""Processing job tracking model."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.paper import Paper


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    PARSE_PDF = "parse_pdf"
    EXTRACT_LLM = "extract_llm"
    GENERATE_OUTPUTS = "generate_outputs"
    FULL_PIPELINE = "full_pipeline"
    FOLDER_SCAN = "folder_scan"


class ProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "processing_jobs"

    paper_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    paper: Mapped[Optional["Paper"]] = relationship("Paper", back_populates="processing_jobs")

    celery_task_id: Mapped[Optional[str]] = mapped_column(String(256), index=True)
    job_type: Mapped[str] = mapped_column(
        Enum(JobType, name="job_type"), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    progress_percent: Mapped[Optional[float]] = mapped_column(Float)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    result_summary: Mapped[Optional[dict]] = mapped_column(JSONB)
    metadata_: Mapped[Optional[dict]] = mapped_column(JSONB, name="metadata")

    def __repr__(self) -> str:
        return f"<ProcessingJob id={self.id} type={self.job_type} status={self.status}>"
