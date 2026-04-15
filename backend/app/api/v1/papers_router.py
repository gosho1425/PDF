"""
Papers endpoints.
GET  /api/papers              → paginated list
GET  /api/papers/{id}         → full detail with extraction
GET  /api/papers/{id}/summary → raw summary text file
DELETE /api/papers/{id}       → remove record (and output files)
POST /api/papers/{id}/reprocess → re-extract a specific paper
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc, asc
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.paper import Paper, PaperStatus

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("")
def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    """List papers with optional filtering and search."""
    q = db.query(Paper)

    if status:
        try:
            q = q.filter(Paper.status == PaperStatus(status))
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    if search:
        like = f"%{search}%"
        q = q.filter(
            Paper.title.ilike(like) |
            Paper.file_name.ilike(like) |
            Paper.journal.ilike(like)
        )

    sort_col = {
        "created_at": Paper.created_at,
        "updated_at": Paper.updated_at,
        "title": Paper.title,
        "year": Paper.year,
        "status": Paper.status,
    }.get(sort_by, Paper.created_at)

    q = q.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))
    total = q.count()
    papers = q.offset(skip).limit(limit).all()

    return {
        "items": [_serialize_list_item(p) for p in papers],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{paper_id}")
def get_paper(paper_id: str, db: Session = Depends(get_db)):
    """Get full paper detail including extraction JSON."""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found")
    return _serialize_full(paper)


@router.get("/{paper_id}/summary", response_class=PlainTextResponse)
def get_summary(paper_id: str, db: Session = Depends(get_db)):
    """Return the plain-text summary file content."""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found")
    if not paper.summary_path:
        raise HTTPException(404, "No summary available yet")
    p = Path(paper.summary_path)
    if not p.exists():
        raise HTTPException(404, "Summary file not found on disk")
    return p.read_text(encoding="utf-8")


@router.post("/{paper_id}/reprocess")
def reprocess_paper(paper_id: str, db: Session = Depends(get_db)):
    """Re-run LLM extraction for a specific paper."""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found")

    from app.services.scanner import _process_one, ScanResult
    from app.core.config import get_settings
    import json as _json
    from app.services.settings_service import get_setting

    raw = get_setting(db, "custom_parameters")
    custom_params = _json.loads(raw) if raw else []

    settings = get_settings()
    result = ScanResult()

    # Reset status so scanner will re-process it
    old_sha = paper.sha256
    paper.sha256 = "REPROCESS_" + old_sha  # temp to bypass dedup
    paper.status = PaperStatus.pending
    db.commit()

    try:
        _process_one(db, Path(paper.file_path), settings, custom_params, result)
    finally:
        # Restore original sha256 if still pending (process_one will update it)
        fresh = db.get(Paper, paper_id)
        if fresh and fresh.sha256.startswith("REPROCESS_"):
            fresh.sha256 = old_sha
            db.commit()

    return {"status": "reprocessed", "new_status": db.get(Paper, paper_id).status.value}


@router.delete("/{paper_id}", status_code=204)
def delete_paper(paper_id: str, db: Session = Depends(get_db)):
    """Delete a paper record and its output files."""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(404, "Paper not found")

    for path_str in [paper.summary_path, paper.extraction_path]:
        if path_str:
            p = Path(path_str)
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

    db.delete(paper)
    db.commit()


# ── Serializers ───────────────────────────────────────────────────────────────

def _serialize_list_item(p: Paper) -> dict:
    return {
        "id":             p.id,
        "file_name":      p.file_name,
        "file_path":      p.file_path,
        "status":         p.status.value,
        "title":          p.title,
        "journal":        p.journal,
        "year":           p.year,
        "authors":        p.authors or [],
        "impact_factor":  p.impact_factor,
        "processed_at":   p.processed_at.isoformat() if p.processed_at else None,
        "created_at":     p.created_at.isoformat(),
        "error_message":  p.error_message,
        "has_extraction": p.extraction is not None,
    }


def _serialize_full(p: Paper) -> dict:
    base = _serialize_list_item(p)
    base.update({
        "sha256":        p.sha256,
        "file_size_bytes": p.file_size_bytes,
        "doi":           p.doi,
        "abstract":      p.abstract,
        "extraction":    p.extraction,
        "summary_path":  p.summary_path,
    })
    return base
