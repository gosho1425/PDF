"""Export request/response schemas."""
from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel


class ExportRequest(BaseModel):
    paper_ids: Optional[List[uuid.UUID]] = None  # None = export all
    format: str = "csv"  # "csv" | "json"
    include_raw_extraction: bool = False
    include_source_evidence: bool = False
