"""
Folder scanner — the core ingestion engine.

Workflow for each PDF found:
  1. Compute SHA-256
  2. Check if already in DB with status=done -> skip
  3. If status=failed (prior attempt) -> allow reprocessing
  4. Extract text
  5. Call LLM for structured extraction
  6. Write summary .txt and extraction .json to data/
  7. Save Paper record to SQLite

Data safety guarantees:
  - Already-processed (done) papers are NEVER re-touched by a normal scan.
  - SHA-256 deduplication means the same PDF content is only processed once.
  - If processing fails the Paper record is kept with status=failed and
    the original SHA-256, so a future reprocess attempt can find it.
  - Output files (summaries/, extractions/) are only written on success.
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


def run_scan(
    db: Session,
    custom_parameters: Optional[list[dict]] = None,
    reprocess_failed: bool = False,
) -> ScanResult:
    """
    Scan the configured folder for new PDFs and process them.

    Args:
        db: SQLAlchemy session
        custom_parameters: override custom extraction params (uses DB value if None)
        reprocess_failed: if True, also reprocess papers with status=failed

    Returns a ScanResult summary.
    Existing successfully processed papers (status=done) are always skipped.
    """
    t0 = time.time()
    result = ScanResult()
    custom_parameters = custom_parameters or []

    # ── Get configured folder ─────────────────────────────────────────────────
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

    # ── Find PDFs ─────────────────────────────────────────────────────────────
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
        try:
            _process_one(
                db, pdf_path, settings, custom_parameters, result,
                reprocess_failed=reprocess_failed,
            )
        except Exception as e:
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
    """Process a single PDF file."""

    # ── SHA-256 dedup ─────────────────────────────────────────────────────────
    sha = sha256_of_file(pdf_path)
    existing = db.query(Paper).filter(Paper.sha256 == sha).first()

    if existing:
        if existing.status == PaperStatus.done:
            log.debug(f"Skipping {pdf_path.name} (already done, id={existing.id})")
            result.skipped += 1
            return

        if existing.status == PaperStatus.failed and not reprocess_failed:
            log.debug(
                f"Skipping {pdf_path.name} (previously failed: {existing.error_message[:80]}). "
                "Use 'Reprocess Failed' to retry."
            )
            result.skipped += 1
            return

        if existing.status in (PaperStatus.failed, PaperStatus.processing):
            # Allow reprocessing
            log.info(
                f"Reprocessing {pdf_path.name} "
                f"(previous status={existing.status.value})"
            )
            paper = existing
            paper.status = PaperStatus.processing
            paper.error_message = None
            db.flush()
        else:
            # pending — process normally
            paper = existing
    else:
        # ── Create new pending record ──────────────────────────────────────────
        paper = Paper(
            file_path=str(pdf_path),
            file_name=pdf_path.name,
            file_size_bytes=pdf_path.stat().st_size,
            sha256=sha,
            status=PaperStatus.processing,
        )
        db.add(paper)
        db.flush()

    try:
        log.info(f"Processing: {pdf_path.name} ({pdf_path.stat().st_size / 1024:.0f} KB)")

        # ── Extract PDF text ──────────────────────────────────────────────────
        text = extract_text(pdf_path)
        text_len = len(text.strip())
        if text_len < 50:
            raise ValueError(
                f"Extracted text too short ({text_len} chars). "
                "The PDF may be scanned/image-only (no machine-readable text). "
                "OCR is not supported in this version."
            )

        log.info(f"Extracted {len(text):,} chars from {pdf_path.name}")

        # ── LLM extraction ────────────────────────────────────────────────────
        provider = get_llm_provider()
        extraction = provider.extract(text, custom_parameters)

        # ── Write output files ────────────────────────────────────────────────
        paper_id = paper.id
        summary_path = _write_summary(settings, paper_id, pdf_path, extraction)
        extraction_path = _write_extraction(settings, paper_id, extraction)

        # ── Update DB record ──────────────────────────────────────────────────
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
        db.rollback()
        error_msg = str(e)
        log.error(f"Failed: {pdf_path.name}: {error_msg}")

        # Re-attach and mark as failed with detailed error
        paper = db.merge(paper)
        paper.status        = PaperStatus.failed
        paper.error_message = _format_error_message(e)
        paper.processed_at  = datetime.utcnow()
        db.commit()

        result.failed += 1
        result.errors.append(f"{pdf_path.name}: {error_msg}")


def _format_error_message(exc: Exception) -> str:
    """
    Format an exception into a human-readable error message stored in the DB.
    This is shown in the UI next to the paper's status badge.
    """
    msg = str(exc)

    # Truncate very long messages (e.g. full API error bodies)
    if len(msg) > 500:
        msg = msg[:497] + "..."

    return msg


def _write_summary(settings, paper_id: str, pdf_path: Path, extraction) -> Path:
    """Write human-readable summary .txt file."""
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
    """Write machine-readable extraction .json file."""
    fname = f"{paper_id}.json"
    out_path = settings.EXTRACTIONS_DIR / fname
    data = extraction.to_dict()
    data["paper_id"] = paper_id
    data["generated_at"] = datetime.utcnow().isoformat()
    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return out_path
