"""
Paper model — one row per PDF file.
Stores file metadata, processing status, and paths to output files.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Enum, Integer, String, Text, Float, Boolean,
)
from sqlalchemy.dialects.sqlite import JSON

from app.db.database import Base


class PaperStatus(str, enum.Enum):
    pending    = "pending"
    processing = "processing"
    done       = "done"
    failed     = "failed"


class Paper(Base):
    __tablename__ = "papers"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # ── File identity ──────────────────────────────────────────────────────────
    file_path       = Column(String(1024), nullable=False, unique=True, index=True)
    file_name       = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    sha256          = Column(String(64), nullable=False, unique=True, index=True)
    # ── Processing ─────────────────────────────────────────────────────────────
    status          = Column(Enum(PaperStatus), nullable=False, default=PaperStatus.pending)
    error_message   = Column(Text, nullable=True)
    processed_at    = Column(DateTime, nullable=True)
    # ── Extracted bibliographic fields ─────────────────────────────────────────
    title           = Column(Text, nullable=True)
    authors         = Column(JSON, nullable=True)          # list[str]
    journal         = Column(String(512), nullable=True)
    year            = Column(Integer, nullable=True)
    doi             = Column(String(256), nullable=True)
    abstract        = Column(Text, nullable=True)
    impact_factor   = Column(Float, nullable=True)
    # ── Structured extraction ──────────────────────────────────────────────────
    # Full structured extraction stored as JSON —
    # includes input_variables, output_variables, material_info, etc.
    extraction      = Column(JSON, nullable=True)
    # ── Output file paths ──────────────────────────────────────────────────────
    summary_path    = Column(String(1024), nullable=True)
    extraction_path = Column(String(1024), nullable=True)
    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at      = Column(DateTime, nullable=False, default=datetime.utcnow,
                             onupdate=datetime.utcnow)
