"""Pydantic schemas for Paper endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.paper import PaperStatus


class PaperCreate(BaseModel):
    original_filename: str = Field(..., max_length=512)


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    doi: Optional[str] = Field(None, max_length=256)
    abstract: Optional[str] = None
    publication_year: Optional[int] = Field(None, ge=1900, le=2100)
    keywords: Optional[List[str]] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None


class PaperStatusUpdate(BaseModel):
    status: PaperStatus


class JournalInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    impact_factor: Optional[float] = None
    impact_factor_year: Optional[int] = None
    impact_factor_status: Optional[str] = None


class AuthorInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    affiliation: Optional[str] = None
    position: int = 0


class PaperListItem(BaseModel):
    """Lightweight representation for table view."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    title: Optional[str] = None
    doi: Optional[str] = None
    publication_year: Optional[int] = None
    status: PaperStatus
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    journal_name: Optional[str] = None
    author_names: Optional[List[str]] = None

    # Top-level extraction fields for table display
    has_extraction: bool = False
    needs_review: bool = False


class PaperRead(BaseModel):
    """Full paper detail including all metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_size_bytes: Optional[int] = None
    file_hash_sha256: Optional[str] = None
    page_count: Optional[int] = None
    status: PaperStatus
    parse_error: Optional[str] = None
    extraction_error: Optional[str] = None

    title: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    keywords: Optional[List[str]] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None

    journal: Optional[JournalInfo] = None
    authors: Optional[List[AuthorInfo]] = None

    parse_method: Optional[str] = None
    schema_version: Optional[str] = None
    summary_path: Optional[str] = None
    extraction_json_path: Optional[str] = None

    created_at: datetime
    updated_at: datetime
