"""
Paper management API endpoints.
All LLM calls are triggered asynchronously via Celery tasks.
The frontend NEVER directly calls Claude or any LLM service.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, HTTPException,
    Query, UploadFile, status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.paper import Paper, PaperStatus
from app.schemas.paper import PaperCreate, PaperListItem, PaperRead, PaperUpdate
from app.services.paper_service import PaperService
from app.services.storage import get_storage
from app.workers.tasks import run_full_pipeline, scan_folder

router = APIRouter()
log = get_logger(__name__)
settings = get_settings()

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=List[dict], status_code=status.HTTP_202_ACCEPTED)
async def upload_papers(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload one or many PDF files.
    Triggers async pipeline (parse + extract) for each file.
    Returns list of paper IDs and initial status.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    storage = get_storage()
    results = []

    # Use sync DB session for file processing (Celery needs sync anyway)
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    for upload in files:
        # Validate
        if not upload.filename:
            continue
        if not upload.filename.lower().endswith(".pdf"):
            results.append({
                "filename": upload.filename,
                "error": "Only PDF files are accepted",
                "status": "rejected",
            })
            continue

        # Size check
        content = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            results.append({
                "filename": upload.filename,
                "error": f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
                "status": "rejected",
            })
            continue

        # Save to storage
        paper_id = uuid.uuid4()
        try:
            import io
            content_io = io.BytesIO(content)

            # Compute hash
            import hashlib
            sha256 = hashlib.sha256(content).hexdigest()
            dest = storage.original_pdf_path(paper_id)
            dest.write_bytes(content)
            rel_path = storage.relative_path(dest)

            # Register in DB (sync)
            with SyncSession() as sync_db:
                service = PaperService(sync_db)
                # Check duplicate
                from sqlalchemy import select
                from app.models.paper import Paper as PaperModel
                existing = sync_db.execute(
                    select(PaperModel).where(PaperModel.file_hash_sha256 == sha256)
                ).scalar_one_or_none()

                if existing:
                    results.append({
                        "filename": upload.filename,
                        "paper_id": str(existing.id),
                        "status": existing.status.value,
                        "message": "Duplicate file detected – using existing record",
                    })
                    continue

                paper = service.create_paper(
                    original_filename=upload.filename,
                    file_path=rel_path,
                    file_hash=sha256,
                    file_size=len(content),
                )
                sync_db.commit()
                paper_id = paper.id

            # Queue pipeline
            task = run_full_pipeline.delay(str(paper_id))
            log.info("Pipeline queued", paper_id=str(paper_id), task_id=task.id)

            results.append({
                "filename": upload.filename,
                "paper_id": str(paper_id),
                "task_id": task.id,
                "status": "queued",
            })

        except Exception as exc:
            log.error("Upload failed", filename=upload.filename, error=str(exc))
            results.append({
                "filename": upload.filename,
                "error": str(exc),
                "status": "failed",
            })

    return results


@router.post("/scan-folder", status_code=status.HTTP_202_ACCEPTED)
async def scan_local_folder(
    folder_path: str = Query(..., description="Absolute path to local folder containing PDFs"),
):
    """
    Scan a configured local folder for PDF files and queue them all for processing.
    The folder must exist on the server filesystem.
    """
    from pathlib import Path
    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=400, detail=f"Folder not found: {folder_path}")
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {folder_path}")

    task = scan_folder.delay(str(folder))
    return {"task_id": task.id, "status": "scanning", "folder": str(folder)}


@router.get("", response_model=dict)
async def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[PaperStatus] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|title|publication_year|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """
    List papers with pagination, filtering, and search.
    Returns metadata suitable for the table view.
    """
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    with SyncSession() as db:
        service = PaperService(db)
        papers, total = service.list_papers(
            skip=skip,
            limit=limit,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        items = []
        for p in papers:
            # Build lightweight list item
            author_names = [pa.author.full_name for pa in (p.paper_authors or [])]
            has_extraction = bool(p.extraction_records)
            needs_review = any(
                r.status == "needs_review" for r in (p.extraction_records or [])
            )
            items.append({
                "id": str(p.id),
                "original_filename": p.original_filename,
                "title": p.title,
                "doi": p.doi,
                "publication_year": p.publication_year,
                "status": p.status.value,
                "page_count": p.page_count,
                "file_size_bytes": p.file_size_bytes,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
                "journal_name": p.journal.name if p.journal else None,
                "author_names": author_names,
                "has_extraction": has_extraction,
                "needs_review": needs_review,
            })

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{paper_id}", response_model=dict)
async def get_paper(paper_id: uuid.UUID):
    """Get full paper details."""
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    with SyncSession() as db:
        service = PaperService(db)
        paper = service.get_paper(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        author_names = [
            {"name": pa.author.full_name, "position": pa.position}
            for pa in (paper.paper_authors or [])
        ]
        return {
            "id": str(paper.id),
            "original_filename": paper.original_filename,
            "file_size_bytes": paper.file_size_bytes,
            "file_hash_sha256": paper.file_hash_sha256,
            "page_count": paper.page_count,
            "status": paper.status.value,
            "parse_error": paper.parse_error,
            "extraction_error": paper.extraction_error,
            "title": paper.title,
            "doi": paper.doi,
            "abstract": paper.abstract,
            "publication_year": paper.publication_year,
            "keywords": paper.keywords,
            "volume": paper.volume,
            "issue": paper.issue,
            "pages": paper.pages,
            "journal": {"id": str(paper.journal.id), "name": paper.journal.name} if paper.journal else None,
            "authors": author_names,
            "parse_method": paper.parse_method,
            "schema_version": paper.schema_version,
            "summary_available": bool(paper.summary_path),
            "extraction_available": bool(paper.extraction_json_path),
            "created_at": paper.created_at.isoformat(),
            "updated_at": paper.updated_at.isoformat(),
        }


@router.patch("/{paper_id}", response_model=dict)
async def update_paper(paper_id: uuid.UUID, update: PaperUpdate):
    """Manually update paper metadata fields."""
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    with SyncSession() as db:
        service = PaperService(db)
        paper = db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        for field, value in update.model_dump(exclude_none=True).items():
            setattr(paper, field, value)
        db.commit()
        return {"id": str(paper.id), "status": "updated"}


@router.post("/{paper_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_paper(
    paper_id: uuid.UUID,
    stage: str = Query("full", pattern="^(full|parse|extract)$"),
):
    """
    Re-run processing for a paper.
    stage: 'full' | 'parse' (parse only) | 'extract' (extraction only, requires parsed text)
    """
    from app.db.base import get_sync_session_factory
    from app.workers.tasks import parse_pdf as task_parse
    from app.workers.tasks import extract_paper as task_extract

    SyncSession = get_sync_session_factory()
    with SyncSession() as db:
        paper = db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

    if stage == "full":
        task = run_full_pipeline.delay(str(paper_id))
    elif stage == "parse":
        task = task_parse.delay(str(paper_id))
    elif stage == "extract":
        task = task_extract.delay(str(paper_id))

    return {"paper_id": str(paper_id), "task_id": task.id, "stage": stage, "status": "queued"}


@router.get("/{paper_id}/summary", response_class=FileResponse)
async def download_summary(paper_id: uuid.UUID):
    """Download the human-readable summary markdown file."""
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    storage = get_storage()
    with SyncSession() as db:
        paper = db.get(Paper, paper_id)
        if not paper or not paper.summary_path:
            raise HTTPException(status_code=404, detail="Summary not available")

    abs_path = storage.get_absolute(paper.summary_path)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Summary file not found on disk")

    return FileResponse(
        path=str(abs_path),
        filename=f"{paper_id}_summary.md",
        media_type="text/markdown",
    )


@router.get("/{paper_id}/extraction-json", response_class=FileResponse)
async def download_extraction_json(paper_id: uuid.UUID):
    """Download the structured extraction.json file."""
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    storage = get_storage()
    with SyncSession() as db:
        paper = db.get(Paper, paper_id)
        if not paper or not paper.extraction_json_path:
            raise HTTPException(status_code=404, detail="Extraction file not available")

    abs_path = storage.get_absolute(paper.extraction_json_path)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Extraction file not found on disk")

    return FileResponse(
        path=str(abs_path),
        filename=f"{paper_id}_extraction.json",
        media_type="application/json",
    )


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(paper_id: uuid.UUID):
    """Delete a paper and all associated files/records."""
    import shutil
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    storage = get_storage()
    with SyncSession() as db:
        paper = db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Delete files
        paper_dir = storage.paper_dir(paper_id)
        if paper_dir.exists():
            shutil.rmtree(paper_dir)

        db.delete(paper)
        db.commit()
