"""
Paper management API endpoints.

Ingestion model: folder-scan only.
  POST /papers/scan          – trigger async scan of the configured INGEST_DIR
  GET  /papers/ingest-status – current folder mount status + last scan result

All LLM calls are triggered asynchronously via Celery tasks.
The frontend NEVER directly calls Claude or any LLM service.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException,
    Query, status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.paper import Paper, PaperStatus
from app.schemas.paper import PaperUpdate
from app.services.paper_service import PaperService
from app.services.storage import get_storage
from app.workers.tasks import run_full_pipeline, scan_folder

router = APIRouter()
log = get_logger(__name__)
settings = get_settings()


# ── Ingestion ──────────────────────────────────────────────────────────────────

@router.get("/ingest-status")
def get_ingest_status():
    """
    Return the configured ingestion folder path and whether it is accessible
    inside the container. Used by the UI to show mount health.

    Performs a real filesystem read (os.listdir) — not just exists() — so that
    permission errors are caught and reported. Counts PDFs case-insensitively
    so .PDF and .pdf files are both counted.

    Also returns environment-level diagnostic fields so the UI / developer can
    see exactly what path the container resolved without needing shell access.
    """
    import os

    # Always re-read from the live settings object (not a stale module-level var).
    # get_settings() is lru_cached so this is effectively free after first call.
    cfg = get_settings()
    ingest_dir = cfg.INGEST_DIR

    # Raw environment variable — useful to distinguish "env var not set" vs
    # "env var set but path is wrong on host".
    ingest_dir_env_raw: Optional[str] = os.environ.get("INGEST_DIR")

    log.info(
        "ingest-status check",
        ingest_dir=str(ingest_dir),
        ingest_dir_env_raw=ingest_dir_env_raw,
    )

    mount_error: Optional[str] = None
    pdf_count: Optional[int] = None
    folder_exists = False
    # True when /ingest appears to be the empty fallback (no real host mount)
    is_fallback_mount = False

    try:
        exists = ingest_dir.exists()
        is_dir = ingest_dir.is_dir() if exists else False
        log.info(
            "ingest-status fs probe",
            path=str(ingest_dir),
            exists=exists,
            is_dir=is_dir,
        )

        if not exists:
            mount_error = (
                f"Path '{ingest_dir}' does not exist inside the container. "
                "The Docker volume mount is missing or the path is wrong."
            )
        elif not is_dir:
            mount_error = f"'{ingest_dir}' exists but is not a directory."
        else:
            # Perform a real directory read — exists()/is_dir() can succeed on
            # a mount point even when the underlying volume isn't actually readable.
            entries = os.listdir(ingest_dir)
            log.info(
                "ingest-status listdir ok",
                path=str(ingest_dir),
                entry_count=len(entries),
            )
            folder_exists = True

            # Count PDFs case-insensitively (handles .PDF, .Pdf on Windows-sourced folders)
            try:
                count = 0
                for root, _dirs, files in os.walk(ingest_dir):
                    for fname in files:
                        if fname.lower().endswith(".pdf"):
                            count += 1
                pdf_count = count
                log.info(
                    "ingest-status pdf count",
                    path=str(ingest_dir),
                    pdf_count=pdf_count,
                )
            except Exception as count_exc:
                log.warning("ingest-status pdf count failed", error=str(count_exc))
                pdf_count = None

            # Detect if this is the fallback empty mount (./data/ingest inside
            # the repo — meaning HOST_PAPER_DIR was not set in .env).
            # Heuristic: folder is empty and contains only .gitkeep
            non_gitkeep = [e for e in entries if e != ".gitkeep"]
            if pdf_count == 0 and len(non_gitkeep) == 0:
                is_fallback_mount = True
                log.info(
                    "ingest-status: looks like fallback empty mount (no PDFs, only .gitkeep)",
                    path=str(ingest_dir),
                )

    except PermissionError as exc:
        mount_error = f"Permission denied reading '{ingest_dir}': {exc}"
        log.warning("ingest-status permission error", error=str(exc))
    except OSError as exc:
        mount_error = f"OS error checking '{ingest_dir}': {exc}"
        log.warning("ingest-status os error", error=str(exc))
    except Exception as exc:
        mount_error = f"Unexpected error: {exc}"
        log.error("ingest-status unexpected error", error=str(exc), exc_info=True)

    hint: Optional[str] = None
    if not folder_exists:
        hint = (
            f"Container path '{ingest_dir}' is not accessible. "
            "Steps to fix:\n"
            "1. Set HOST_PAPER_DIR in .env to your PDF folder (no # comments or trailing spaces).\n"
            "2. On Windows, add COMPOSE_CONVERT_WINDOWS_PATHS=1 to .env.\n"
            "3. Make sure the host folder actually exists (create it if needed).\n"
            "4. Run: docker compose down && docker compose up -d\n"
            "5. Then click Refresh in the UI."
        )
    elif is_fallback_mount:
        hint = (
            "The folder is mounted but appears to be the empty fallback directory "
            "(data/ingest inside the project). "
            "To use your own PDF folder, set HOST_PAPER_DIR in .env to your PDF folder path "
            "and restart: docker compose down && docker compose up -d"
        )

    log.info(
        "ingest-status result",
        ingest_dir=str(ingest_dir),
        mounted=folder_exists,
        is_fallback_mount=is_fallback_mount,
        pdf_count=pdf_count,
        mount_error=mount_error,
    )

    return {
        "ingest_dir": str(ingest_dir),
        "mounted": folder_exists,
        "pdf_count_in_folder": pdf_count,
        "mount_error": mount_error,
        "hint": hint,
        # Diagnostic fields — help users confirm the right env vars are loaded
        "ingest_dir_from_env": ingest_dir_env_raw or "(not set — using default /ingest)",
        "is_fallback_mount": is_fallback_mount,
    }


@router.post("/scan", status_code=status.HTTP_202_ACCEPTED)
def trigger_scan():
    """
    Trigger an asynchronous scan of the configured INGEST_DIR.
    The Celery worker will:
      1. Recursively find all *.pdf files.
      2. Compute SHA-256 for each; skip duplicates already in the database.
      3. Copy new PDFs to managed storage, create Paper records, queue parse→extract.
    Returns a task_id that can be polled via GET /jobs/{task_id}/celery-status.
    """
    ingest_dir = settings.INGEST_DIR
    if not ingest_dir.exists() or not ingest_dir.is_dir():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Ingestion folder '{ingest_dir}' is not accessible inside the container. "
                "Mount your host PDF folder as a Docker volume. "
                "See README – 'Folder-based Ingestion' for Windows/macOS/Linux instructions."
            ),
        )

    task = scan_folder.delay()
    log.info("Folder scan triggered", ingest_dir=str(ingest_dir), task_id=task.id)
    return {
        "task_id": task.id,
        "status": "scanning",
        "ingest_dir": str(ingest_dir),
        "message": (
            "Scan started. Poll GET /api/v1/jobs/{task_id}/celery-status for progress. "
            "Duplicate PDFs (matched by SHA-256) will be skipped automatically."
        ),
    }


# ── Papers list & detail ───────────────────────────────────────────────────────

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
