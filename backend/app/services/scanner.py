"""
Folder scanner — the core ingestion engine.

Workflow for each PDF found:
  1. Compute SHA-256
  2. Check if already in DB → skip if yes
  3. Extract text
  4. Call LLM for structured extraction
  5. Write summary .txt and extraction .json to data/
  6. Save Paper record to SQLite
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


def run_scan(db: Session, custom_parameters: Optional[list[dict]] = None) -> ScanResult:
    """
    Scan the configured folder for new PDFs and process them.
    Returns a ScanResult summary.
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
    pdf_files = sorted(folder.rglob("*.pdf"))
    # Also find .PDF (case-insensitive for Windows)
    pdf_files_upper = sorted(folder.rglob("*.PDF"))
    seen = set(p.resolve() for p in pdf_files)
    for p in pdf_files_upper:
        if p.resolve() not in seen:
            pdf_files.append(p)
            seen.add(p.resolve())

    result.total_found = len(pdf_files)
    log.info(f"Found {result.total_found} PDF(s)")

    settings = get_settings()

    for pdf_path in pdf_files:
        try:
            _process_one(db, pdf_path, settings, custom_parameters, result)
        except Exception as e:
            log.error(f"Unexpected error processing {pdf_path.name}: {e}", exc_info=True)
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
) -> None:
    """Process a single PDF file."""

    # ── SHA-256 dedup ─────────────────────────────────────────────────────────
    sha = sha256_of_file(pdf_path)
    existing = db.query(Paper).filter(Paper.sha256 == sha).first()
    if existing:
        log.debug(f"Skipping {pdf_path.name} (already processed, id={existing.id})")
        result.skipped += 1
        return

    # ── Create pending record ─────────────────────────────────────────────────
    paper = Paper(
        file_path=str(pdf_path),
        file_name=pdf_path.name,
        file_size_bytes=pdf_path.stat().st_size,
        sha256=sha,
        status=PaperStatus.processing,
    )
    db.add(paper)
    db.flush()  # get the id without committing

    try:
        log.info(f"Processing: {pdf_path.name}")

        # ── Extract PDF text ──────────────────────────────────────────────────
        text = extract_text(pdf_path)
        if len(text.strip()) < 50:
            raise ValueError("Extracted text too short — may be a scanned/image PDF.")

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
        log.info(f"Done: {pdf_path.name} → {extraction.title or '(no title)'}")

    except Exception as e:
        db.rollback()
        log.error(f"Failed: {pdf_path.name}: {e}")
        # Re-attach and mark as failed
        paper = db.merge(paper)
        paper.status = PaperStatus.failed
        paper.error_message = str(e)
        paper.processed_at = datetime.utcnow()
        db.commit()
        result.failed += 1
        result.errors.append(f"{pdf_path.name}: {e}")


def _write_summary(settings, paper_id: str, pdf_path: Path, extraction) -> Path:
    """Write human-readable summary .txt file."""
    stem = pdf_path.stem[:80]  # limit filename length
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
        "─" * 60,
        "SUMMARY",
        "─" * 60,
        extraction.raw_summary or "(No summary generated)",
        "",
        "─" * 60,
        "MATERIAL",
        "─" * 60,
    ]
    for k, fv in extraction.material_info.items():
        if fv.value is not None:
            unit = f" {fv.unit}" if fv.unit else ""
            lines.append(f"  {k}: {fv.value}{unit}  [conf={fv.confidence:.2f}]")

    lines += ["", "─" * 60, "INPUT VARIABLES (controllable)", "─" * 60]
    for k, fv in extraction.input_variables.items():
        if fv.value is not None:
            unit = f" {fv.unit}" if fv.unit else ""
            lines.append(f"  {k}: {fv.value}{unit}  [conf={fv.confidence:.2f}]")
            if fv.evidence:
                lines.append(f"    Evidence: \"{fv.evidence[:120]}\"")

    lines += ["", "─" * 60, "OUTPUT VARIABLES (measured)", "─" * 60]
    for k, fv in extraction.output_variables.items():
        if fv.value is not None:
            unit = f" {fv.unit}" if fv.unit else ""
            lines.append(f"  {k}: {fv.value}{unit}  [conf={fv.confidence:.2f}]")
            if fv.evidence:
                lines.append(f"    Evidence: \"{fv.evidence[:120]}\"")

    lines += ["", f"Generated by PaperLens v2 — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _write_extraction(settings, paper_id: str, extraction) -> Path:
    """Write machine-readable extraction .json file."""
    fname = f"{paper_id}.json"
    out_path = settings.EXTRACTIONS_DIR / fname
    data = extraction.to_dict()
    data["paper_id"] = paper_id
    data["generated_at"] = datetime.utcnow().isoformat()
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path
