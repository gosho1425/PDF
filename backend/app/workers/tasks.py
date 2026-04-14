"""
Celery tasks for the paper processing pipeline.

Task graph:
  run_full_pipeline
    ├── parse_pdf
    └── extract_paper
           └── generate_outputs
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from celery import Task
from celery.utils.log import get_task_logger

from app.core.config import get_settings
from app.db.base import get_sync_session_factory
from app.models.job import JobStatus, JobType, ProcessingJob
from app.models.paper import Paper, PaperStatus
from app.services.llm_extractor import LLMExtractor, ExtractorError
from app.services.output_generator import OutputGenerator
from app.services.paper_service import PaperService
from app.services.pdf_parser import PDFParser
from app.services.storage import get_storage
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)
settings = get_settings()


def _get_db_session():
    """Get a synchronous DB session for use in Celery workers."""
    SessionLocal = get_sync_session_factory()
    return SessionLocal()


class BaseTask(Task):
    """Base task with error handling and DB session management."""
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {self.name} failed: {exc}", exc_info=True)


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="app.workers.tasks.parse_pdf",
    max_retries=3,
    default_retry_delay=30,
)
def parse_pdf(self, paper_id: str, job_id: Optional[str] = None) -> dict:
    """
    Task 1: Parse a PDF file and extract text + metadata.
    Updates the Paper record in the database.
    """
    paper_uuid = uuid.UUID(paper_id)
    logger.info(f"Starting PDF parse for paper {paper_id}")

    db = _get_db_session()
    try:
        service = PaperService(db)
        paper = db.get(Paper, paper_uuid)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        # Update status
        paper.status = PaperStatus.PARSING
        db.commit()

        # Parse
        storage = get_storage()
        pdf_path = storage.get_absolute(paper.file_path)
        parser = PDFParser()
        parsed = parser.parse(pdf_path)

        if not parsed.total_text.strip():
            raise ValueError("PDF parsing yielded empty text")

        # Update paper
        service.update_paper_from_parse(
            paper=paper,
            title=parsed.title,
            doi=parsed.doi,
            abstract=parsed.abstract,
            year=parsed.year,
            page_count=parsed.page_count,
            raw_text=parsed.total_text,
            parse_method=parsed.parse_method,
        )

        # Handle authors (basic heuristic - LLM will do better)
        if parsed.metadata.get("Author"):
            raw_authors = parsed.metadata["Author"]
            # Try splitting on common separators
            author_names = [a.strip() for a in raw_authors.replace(";", ",").split(",") if a.strip()]
            if author_names:
                service.attach_authors(paper, author_names)

        db.commit()
        logger.info(f"PDF parse complete for paper {paper_id}, pages={parsed.page_count}")
        return {
            "paper_id": paper_id,
            "status": "parsed",
            "page_count": parsed.page_count,
            "parse_method": parsed.parse_method,
            "text_length": len(parsed.total_text),
        }

    except Exception as exc:
        db.rollback()
        paper = db.get(Paper, paper_uuid)
        if paper:
            paper.status = PaperStatus.FAILED
            paper.parse_error = str(exc)
            db.commit()
        logger.error(f"PDF parse failed for {paper_id}: {exc}")
        raise self.retry(exc=exc) if self.request.retries < self.max_retries else exc
    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="app.workers.tasks.extract_paper",
    max_retries=2,
    default_retry_delay=60,
)
def extract_paper(self, paper_id: str, job_id: Optional[str] = None) -> dict:
    """
    Task 2: LLM-based scientific data extraction.
    Reads parsed text from DB, calls Claude, saves structured results.
    """
    paper_uuid = uuid.UUID(paper_id)
    logger.info(f"Starting LLM extraction for paper {paper_id}")

    db = _get_db_session()
    try:
        service = PaperService(db)
        paper = db.get(Paper, paper_uuid)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        if not paper.raw_text:
            raise ValueError(f"Paper {paper_id} has no parsed text; run parse_pdf first")

        # Update status
        paper.status = PaperStatus.EXTRACTING
        db.commit()

        # Build ParsedPDF object from stored data
        from app.services.pdf_parser import ParsedPDF, ParsedPage
        parsed = ParsedPDF(
            total_text=paper.raw_text,
            page_count=paper.page_count or 0,
        )

        # Run LLM extraction
        extractor = LLMExtractor()
        extraction_output = extractor.extract(parsed)

        # Update bibliographic data from LLM (more accurate than heuristics)
        if bib := extraction_output.bibliographic_info:
            if bib.title and not paper.title:
                paper.title = bib.title
            if bib.doi and not paper.doi:
                paper.doi = bib.doi
            if bib.abstract and not paper.abstract:
                paper.abstract = bib.abstract
            if bib.year and not paper.publication_year:
                paper.publication_year = bib.year
            if bib.volume:
                paper.volume = bib.volume
            if bib.issue:
                paper.issue = bib.issue
            if bib.pages:
                paper.pages = bib.pages
            if bib.keywords:
                paper.keywords = bib.keywords
            if bib.authors:
                service.attach_authors(paper, bib.authors)
            if bib.journal:
                journal = service.get_or_create_journal(bib.journal)
                paper.journal_id = journal.id

        # Generate output files
        storage = get_storage()
        generator = OutputGenerator()

        summary_path_abs = generator.generate_summary(
            paper=paper,
            extraction=extraction_output,
            paper_id=paper_uuid,
        )
        extraction_json_path_abs = generator.generate_extraction_json(
            extraction=extraction_output,
            paper_id=paper_uuid,
            paper_metadata={
                "original_filename": paper.original_filename,
                "file_hash": paper.file_hash_sha256,
            },
        )

        # Save to DB
        record = service.save_extraction(
            paper=paper,
            extraction_output=extraction_output,
            llm_model=settings.ANTHROPIC_MODEL,
            schema_version=settings.SCHEMA_VERSION,
            summary_path=storage.relative_path(summary_path_abs),
            extraction_json_path=storage.relative_path(extraction_json_path_abs),
        )

        db.commit()
        logger.info(f"Extraction complete for paper {paper_id}, record={record.id}")
        return {
            "paper_id": paper_id,
            "extraction_record_id": str(record.id),
            "status": "extracted",
            "needs_review": bool(extraction_output.fields_needing_review),
            "warnings": extraction_output.extraction_warnings,
        }

    except ExtractorError as exc:
        db.rollback()
        paper = db.get(Paper, paper_uuid)
        if paper:
            paper.status = PaperStatus.FAILED
            paper.extraction_error = str(exc)
            db.commit()
        logger.error(f"LLM extraction failed for {paper_id}: {exc}")
        # Don't retry LLM auth errors
        if "authentication" in str(exc).lower() or "api_key" in str(exc).lower():
            raise exc
        raise self.retry(exc=exc) if self.request.retries < self.max_retries else exc
    except Exception as exc:
        db.rollback()
        paper = db.get(Paper, paper_uuid)
        if paper:
            paper.status = PaperStatus.FAILED
            paper.extraction_error = str(exc)
            db.commit()
        logger.error(f"Extraction failed for {paper_id}: {exc}")
        raise self.retry(exc=exc) if self.request.retries < self.max_retries else exc
    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="app.workers.tasks.run_full_pipeline",
    max_retries=1,
)
def run_full_pipeline(self, paper_id: str, job_id: Optional[str] = None) -> dict:
    """
    Orchestrator task: runs parse → extract in sequence for a single paper.
    """
    logger.info(f"Starting full pipeline for paper {paper_id}")

    # Run synchronously within this task (keeps ordering guaranteed)
    parse_result = parse_pdf.apply(args=[paper_id]).get(timeout=300)
    extract_result = extract_paper.apply(args=[paper_id]).get(timeout=600)

    return {
        "paper_id": paper_id,
        "parse_result": parse_result,
        "extract_result": extract_result,
        "status": "complete",
    }


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="app.workers.tasks.scan_folder",
    max_retries=1,
)
def scan_folder(self, folder_path: str, job_id: Optional[str] = None) -> dict:
    """
    Scan a local folder for PDF files and queue them for processing.
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder does not exist: {folder_path}")

    pdf_files = list(folder.glob("*.pdf")) + list(folder.glob("**/*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDFs in {folder_path}")

    db = _get_db_session()
    queued = []
    try:
        storage = get_storage()
        service = PaperService(db)

        for pdf_file in pdf_files:
            new_paper_id = uuid.uuid4()
            dest_path, sha256, size = storage.copy_from_folder(pdf_file, new_paper_id)
            rel_path = storage.relative_path(dest_path)

            paper = service.create_paper(
                original_filename=pdf_file.name,
                file_path=rel_path,
                file_hash=sha256,
                file_size=size,
            )
            db.commit()

            # Queue pipeline
            run_full_pipeline.delay(str(paper.id))
            queued.append(str(paper.id))

        return {"queued": queued, "total": len(queued)}
    finally:
        db.close()
