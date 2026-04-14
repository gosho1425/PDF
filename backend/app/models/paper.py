"""
Core Paper model – represents a single research paper PDF.
"""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.author import PaperAuthor
    from app.models.extraction import ExtractionRecord
    from app.models.job import ProcessingJob
    from app.models.journal import Journal


class PaperStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    REVIEW_NEEDED = "review_needed"
    FAILED = "failed"


class Paper(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Represents a single research paper ingested into the system.
    All file paths are relative to DATA_DIR so the storage backend can be swapped.
    """
    __tablename__ = "papers"

    # ── File tracking ──────────────────────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)  # relative path
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    file_hash_sha256: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)

    # ── Status ─────────────────────────────────────────────────────────────────
    status: Mapped[PaperStatus] = mapped_column(
        Enum(PaperStatus, name="paper_status"),
        default=PaperStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    parse_error: Mapped[Optional[str]] = mapped_column(Text)
    extraction_error: Mapped[Optional[str]] = mapped_column(Text)

    # ── Bibliographic metadata (from PDF parsing) ──────────────────────────────
    title: Mapped[Optional[str]] = mapped_column(Text)
    doi: Mapped[Optional[str]] = mapped_column(String(256), index=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    publication_year: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    keywords: Mapped[Optional[list]] = mapped_column(JSONB)  # list[str]

    # ── Volume / Issue / Pages ─────────────────────────────────────────────────
    volume: Mapped[Optional[str]] = mapped_column(String(64))
    issue: Mapped[Optional[str]] = mapped_column(String(64))
    pages: Mapped[Optional[str]] = mapped_column(String(64))

    # ── Journal FK ────────────────────────────────────────────────────────────
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id"), index=True
    )
    journal: Mapped[Optional["Journal"]] = relationship("Journal", back_populates="papers")

    # ── Relationships ──────────────────────────────────────────────────────────
    paper_authors: Mapped[List["PaperAuthor"]] = relationship(
        "PaperAuthor", back_populates="paper", cascade="all, delete-orphan",
        order_by="PaperAuthor.position",
    )
    extraction_records: Mapped[List["ExtractionRecord"]] = relationship(
        "ExtractionRecord", back_populates="paper", cascade="all, delete-orphan",
    )
    processing_jobs: Mapped[List["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="paper", cascade="all, delete-orphan",
    )

    # ── Output file paths (relative to DATA_DIR) ──────────────────────────────
    summary_path: Mapped[Optional[str]] = mapped_column(String(1024))
    extraction_json_path: Mapped[Optional[str]] = mapped_column(String(1024))

    # ── Raw parsed text cache ─────────────────────────────────────────────────
    raw_text: Mapped[Optional[str]] = mapped_column(Text)   # full extracted text
    parse_method: Mapped[Optional[str]] = mapped_column(String(32))  # "native" | "ocr" | "hybrid"

    # ── Schema version used during extraction ─────────────────────────────────
    schema_version: Mapped[Optional[str]] = mapped_column(String(32))

    def __repr__(self) -> str:
        return f"<Paper id={self.id} title={self.title!r} status={self.status}>"
