"""
Folder scanner — the core ingestion engine.

Workflow for each PDF found:
  1. Compute SHA-256
  2. Look up by BOTH sha256 AND file_path to find any existing record
  3. Skip if already done
  4. Extract text
  5. Call LLM for structured extraction
  6. Write summary .txt and extraction .json to data/
  7. Save Paper record to SQLite

Each PDF is processed in its own try/except + rollback so one failure
never poisons the DB session for the rest of the scan.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.llm.factory import get_llm_provider
from app.models.paper import Paper, PaperStatus
from app.services.pdf_reader import extract_text
from app.services.settings_service import get_setting

log = logging.getLogger(__name__)


@dataclass
class ScanResult:
    total_found: int = 0
    new_processed: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_existing(db: Session, sha: str, file_path: str) -> Optional[Paper]:
    """
    Find an existing Paper record by sha256 OR file_path.

    We check both because:
    - sha256 match: same content, possibly moved/renamed
    - file_path match: same location, content may have changed (re-downloaded PDF)

    Returns the most relevant existing record, or None.
    """
    # Primary: sha256 match (same content)
    by_sha = db.query(Paper).filter(Paper.sha256 == sha).first()
    if by_sha:
        return by_sha

    # Secondary: file_path match (same location, content changed)
    by_path = db.query(Paper).filter(Paper.file_path == file_path).first()
    if by_path:
        return by_path

    return None


def run_scan(
    db: Session,
    custom_parameters: Optional[list[dict]] = None,
    reprocess_failed: bool = False,
) -> ScanResult:
    """
    Scan the configured folder for new PDFs and process them.

    - Already-done papers (status=done) are always skipped.
    - Failed papers are skipped unless reprocess_failed=True.
    - Each PDF is processed in isolation: one failure never stops the rest.
    """
    t0 = time.time()
    result = ScanResult()
    custom_parameters = custom_parameters or []

    folder_str = get_setting(db, "paper_folder")
    if not folder_str:
        raise ValueError(
            "Paper folder not configured. "
            "Open the app and set the folder path in Settings."
        )

    folder = Path(folder_str)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(
            f"Configured folder does not exist: {folder}\n"
            "Update the folder path in Settings."
        )

    log.info(f"Scanning folder: {folder}")

    # Find all PDFs (case-insensitive, deduplicated by resolved path)
    pdf_files: list[Path] = []
    seen: set[Path] = set()
    for pattern in ("*.pdf", "*.PDF"):
        for p in folder.rglob(pattern):
            rp = p.resolve()
            if rp not in seen:
                pdf_files.append(p)
                seen.add(rp)
    pdf_files.sort(key=lambda p: p.name.lower())

    result.total_found = len(pdf_files)
    log.info(f"Found {result.total_found} PDF(s)")

    settings = get_settings()

    for pdf_path in pdf_files:
        # Each PDF gets a fresh, isolated try/except.
        # On any error we rollback THIS paper only, then continue.
        try:
            _process_one(
                db, pdf_path, settings, custom_parameters, result,
                reprocess_failed=reprocess_failed,
            )
        except Exception as e:
            # Make sure the session is clean for the next iteration
            try:
                db.rollback()
            except Exception:
                pass
            log.error(
                f"Unexpected error processing {pdf_path.name}: {e}",
                exc_info=True,
            )
            result.failed += 1
            result.errors.append(f"{pdf_path.name}: {e}")

    result.duration_seconds = round(time.time() - t0, 1)
    log.info(
        f"Scan complete — found={result.total_found}, "
        f"new={result.new_processed}, skipped={result.skipped}, "
        f"failed={result.failed}, time={result.duration_seconds}s"
    )
    return result


def _process_one(
    db: Session,
    pdf_path: Path,
    settings,
    custom_parameters: list[dict],
    result: ScanResult,
    reprocess_failed: bool = False,
) -> None:
    """
    Process a single PDF file.

    This function must always leave the DB session in a clean (committed or
    rolled-back) state when it returns, so the caller can continue with the
    next file.
    """
    file_path_str = str(pdf_path)

    # ── Compute SHA-256 ───────────────────────────────────────────────────────
    try:
        sha = sha256_of_file(pdf_path)
    except OSError as e:
        log.error(f"Cannot read {pdf_path.name}: {e}")
        result.failed += 1
        result.errors.append(f"{pdf_path.name}: Cannot read file — {e}")
        return

    # ── Look up existing record (by sha256 OR file_path) ─────────────────────
    existing = _find_existing(db, sha, file_path_str)

    if existing:
        if existing.status == PaperStatus.done:
            log.debug(f"Skipping {pdf_path.name} (already done, id={existing.id})")
            result.skipped += 1
            return

        if existing.status == PaperStatus.failed and not reprocess_failed:
            err_preview = (existing.error_message or "")[:80]
            log.debug(
                f"Skipping {pdf_path.name} (previously failed: {err_preview}). "
                "Use 'Reprocess Failed' to retry."
            )
            result.skipped += 1
            return

        # Reuse existing record, reset it for reprocessing
        log.info(
            f"Reprocessing {pdf_path.name} "
            f"(previous status={existing.status.value})"
        )
        paper = existing
        # Update file_path in case the file moved
        paper.file_path = file_path_str
        paper.sha256 = sha
        paper.status = PaperStatus.processing
        paper.error_message = None
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            log.warning(f"Integrity error updating {pdf_path.name} — skipping")
            result.skipped += 1
            return

    else:
        # ── Create a new record ───────────────────────────────────────────────
        paper = Paper(
            file_path=file_path_str,
            file_name=pdf_path.name,
            file_size_bytes=pdf_path.stat().st_size,
            sha256=sha,
            status=PaperStatus.processing,
        )
        db.add(paper)
        try:
            db.flush()  # assigns paper.id, checks UNIQUE constraints
        except IntegrityError as e:
            db.rollback()
            # Race condition or leftover record from a previous crash.
            # Try to find the record that caused the conflict and skip.
            log.warning(
                f"Integrity error inserting {pdf_path.name} — "
                f"record already exists. Skipping. ({e})"
            )
            result.skipped += 1
            return

    # ── At this point paper is in DB with status=processing ───────────────────
    paper_id = paper.id

    try:
        log.info(
            f"Processing: {pdf_path.name} "
            f"({pdf_path.stat().st_size / 1024:.0f} KB)"
        )

        # Extract PDF text
        text = extract_text(pdf_path)
        text_len = len(text.strip())
        if text_len < 50:
            raise ValueError(
                f"Extracted text too short ({text_len} chars). "
                "The PDF may be scanned/image-only (no machine-readable text). "
                "OCR is not supported in this version."
            )

        log.info(f"Extracted {len(text):,} chars from {pdf_path.name}")

        # LLM extraction
        provider = get_llm_provider()
        extraction = provider.extract(text, custom_parameters)

        # Write output files
        summary_path    = _write_summary(settings, paper_id, pdf_path, extraction)
        extraction_path = _write_extraction(settings, paper_id, extraction)

        # Update DB record
        paper.status          = PaperStatus.done
        paper.processed_at    = datetime.utcnow()
        paper.title           = extraction.title
        paper.authors         = extraction.authors
        paper.journal         = extraction.journal
        paper.year            = extraction.year
        paper.doi             = extraction.doi
        paper.abstract        = extraction.abstract
        paper.impact_factor   = extraction.impact_factor
        paper.extraction      = extraction.to_dict()
        paper.summary_path    = str(summary_path)
        paper.extraction_path = str(extraction_path)
        paper.error_message   = None

        db.commit()
        result.new_processed += 1
        log.info(f"Done: {pdf_path.name} -> {extraction.title or '(no title)'}")

    except Exception as e:
        # Roll back this paper's changes
        try:
            db.rollback()
        except Exception:
            pass

        error_msg = _format_error_message(e)
        log.error(f"Failed: {pdf_path.name}: {error_msg}")

        # Re-fetch the paper record (session was rolled back) and mark failed
        try:
            paper_record = db.get(Paper, paper_id)
            if paper_record is None:
                # Record was rolled back too (e.g. it was new and flush failed)
                # Re-insert a minimal failed record so it shows in the UI
                paper_record = Paper(
                    file_path=file_path_str,
                    file_name=pdf_path.name,
                    file_size_bytes=pdf_path.stat().st_size if pdf_path.exists() else 0,
                    sha256=sha,
                    status=PaperStatus.failed,
                    error_message=error_msg,
                    processed_at=datetime.utcnow(),
                )
                db.add(paper_record)
            else:
                paper_record.status        = PaperStatus.failed
                paper_record.error_message = error_msg
                paper_record.processed_at  = datetime.utcnow()
            db.commit()
        except Exception as db_err:
            log.error(
                f"Could not save failed status for {pdf_path.name}: {db_err}"
            )
            try:
                db.rollback()
            except Exception:
                pass

        result.failed += 1
        result.errors.append(f"{pdf_path.name}: {error_msg}")


def _format_error_message(exc: Exception) -> str:
    msg = str(exc)
    if len(msg) > 500:
        msg = msg[:497] + "..."
    return msg


def _write_summary(settings, paper_id: str, pdf_path: Path, extraction) -> Path:
    stem = pdf_path.stem[:80]
    fname = f"{stem}_{paper_id[:8]}.txt"
    out_path = settings.SUMMARIES_DIR / fname

    lines = [
        f"# {extraction.title or pdf_path.name}",
        "",
        f"File:    {pdf_path.name}",
        f"Journal: {extraction.journal or 'N/A'}",
        f"Year:    {extraction.year or 'N/A'}",
        f"Authors: {', '.join(extraction.authors) if extraction.authors else 'N/A'}",
        f"DOI:     {extraction.doi or 'N/A'}",
        "",
        "-" * 60,
        "SUMMARY",
        "-" * 60,
        extraction.raw_summary or "(No summary generated)",
        "",
        "-" * 60,
        "MATERIAL",
        "-" * 60,
    ]
    for k, fv in extraction.material_info.items():
        if fv.value is not None:
            unit = f" {fv.unit}" if fv.unit else ""
            lines.append(f"  {k}: {fv.value}{unit}  [conf={fv.confidence:.2f}]")

    lines += ["", "-" * 60, "INPUT VARIABLES (controllable)", "-" * 60]
    for k, fv in extraction.input_variables.items():
        if fv.value is not None:
            unit = f" {fv.unit}" if fv.unit else ""
            lines.append(f"  {k}: {fv.value}{unit}  [conf={fv.confidence:.2f}]")
            if fv.evidence:
                lines.append(f'    Evidence: "{fv.evidence[:120]}"')

    lines += ["", "-" * 60, "OUTPUT VARIABLES (measured)", "-" * 60]
    for k, fv in extraction.output_variables.items():
        if fv.value is not None:
            unit = f" {fv.unit}" if fv.unit else ""
            lines.append(f"  {k}: {fv.value}{unit}  [conf={fv.confidence:.2f}]")
            if fv.evidence:
                lines.append(f'    Evidence: "{fv.evidence[:120]}"')

    lines += [
        "",
        f"Generated by PaperLens v2 -- {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _write_extraction(settings, paper_id: str, extraction) -> Path:
    fname = f"{paper_id}.json"
    out_path = settings.EXTRACTIONS_DIR / fname
    data = extraction.to_dict()
    data["paper_id"] = paper_id
    data["generated_at"] = datetime.utcnow().isoformat()
    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return out_path
