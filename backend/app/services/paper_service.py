"""
Paper CRUD service layer.
Handles business logic between API endpoints and the database.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger
from app.models.author import Author, PaperAuthor
from app.models.extraction import ExtractionRecord, ExtractionStatus
from app.models.job import ProcessingJob, JobStatus, JobType
from app.models.journal import Journal
from app.models.paper import Paper, PaperStatus
from app.schemas.extraction import LLMExtractionOutput
from app.services.storage import get_storage

log = get_logger(__name__)


class PaperService:

    def __init__(self, db: Session):
        self.db = db
        self.storage = get_storage()

    # ── Paper CRUD ─────────────────────────────────────────────────────────────

    def create_paper(
        self,
        original_filename: str,
        file_path: str,
        file_hash: str,
        file_size: int,
    ) -> Paper:
        """Register a new paper record."""
        # Check for duplicate by hash
        existing = self.db.execute(
            select(Paper).where(Paper.file_hash_sha256 == file_hash)
        ).scalar_one_or_none()
        if existing:
            log.info("Duplicate PDF detected", hash=file_hash, existing_id=str(existing.id))
            return existing

        paper = Paper(
            original_filename=original_filename,
            file_path=file_path,
            file_hash_sha256=file_hash,
            file_size_bytes=file_size,
            status=PaperStatus.UPLOADED,
        )
        self.db.add(paper)
        self.db.flush()  # get the ID
        log.info("Paper registered", paper_id=str(paper.id), filename=original_filename)
        return paper

    def get_paper(self, paper_id: uuid.UUID) -> Optional[Paper]:
        return self.db.execute(
            select(Paper)
            .where(Paper.id == paper_id)
            .options(
                selectinload(Paper.journal),
                selectinload(Paper.paper_authors).selectinload(PaperAuthor.author),
                selectinload(Paper.extraction_records),
            )
        ).scalar_one_or_none()

    def list_papers(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[PaperStatus] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Paper], int]:
        """Return paginated list of papers with total count."""
        query = select(Paper).options(
            selectinload(Paper.journal),
            selectinload(Paper.paper_authors).selectinload(PaperAuthor.author),
        )

        if status:
            query = query.where(Paper.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                Paper.title.ilike(search_term)
                | Paper.doi.ilike(search_term)
                | Paper.original_filename.ilike(search_term)
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        # Sort
        sort_col = getattr(Paper, sort_by, Paper.created_at)
        if sort_order == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        papers = list(self.db.execute(query.offset(skip).limit(limit)).scalars().all())
        return papers, total

    def update_paper_status(
        self, paper: Paper, status: PaperStatus, error: Optional[str] = None
    ) -> Paper:
        paper.status = status
        if error and status == PaperStatus.FAILED:
            paper.extraction_error = error
        self.db.flush()
        return paper

    def update_paper_from_parse(
        self,
        paper: Paper,
        title: Optional[str],
        doi: Optional[str],
        abstract: Optional[str],
        year: Optional[int],
        page_count: int,
        raw_text: str,
        parse_method: str,
    ) -> Paper:
        """Update paper record after PDF parsing."""
        if title and not paper.title:
            paper.title = title
        if doi and not paper.doi:
            paper.doi = doi
        if abstract and not paper.abstract:
            paper.abstract = abstract
        if year and not paper.publication_year:
            paper.publication_year = year
        paper.page_count = page_count
        paper.raw_text = raw_text
        paper.parse_method = parse_method
        paper.status = PaperStatus.PARSED
        self.db.flush()
        return paper

    # ── Author / Journal helpers ───────────────────────────────────────────────

    def get_or_create_journal(self, journal_name: str) -> Journal:
        existing = self.db.execute(
            select(Journal).where(Journal.name == journal_name)
        ).scalar_one_or_none()
        if existing:
            return existing
        journal = Journal(name=journal_name)
        self.db.add(journal)
        self.db.flush()
        return journal

    def get_or_create_author(self, full_name: str) -> Author:
        existing = self.db.execute(
            select(Author).where(Author.full_name == full_name)
        ).scalar_one_or_none()
        if existing:
            return existing
        parts = full_name.strip().split()
        author = Author(
            full_name=full_name,
            last_name=parts[-1] if parts else None,
            first_name=" ".join(parts[:-1]) if len(parts) > 1 else None,
        )
        self.db.add(author)
        self.db.flush()
        return author

    def attach_authors(
        self, paper: Paper, author_names: List[str]
    ) -> None:
        """Create/update author associations for a paper."""
        # Remove existing associations
        self.db.execute(
            PaperAuthor.__table__.delete().where(PaperAuthor.paper_id == paper.id)
        )
        for i, name in enumerate(author_names):
            author = self.get_or_create_author(name)
            pa = PaperAuthor(
                paper_id=paper.id,
                author_id=author.id,
                position=i,
            )
            self.db.add(pa)
        self.db.flush()

    # ── Extraction ─────────────────────────────────────────────────────────────

    def save_extraction(
        self,
        paper: Paper,
        extraction_output: LLMExtractionOutput,
        llm_model: str,
        schema_version: str,
        summary_path: Optional[str] = None,
        extraction_json_path: Optional[str] = None,
    ) -> ExtractionRecord:
        """
        Persist an LLMExtractionOutput to the database.
        Marks any previous canonical record as non-canonical.
        """
        from app.models.extraction import (
            MaterialEntity, ProcessCondition, MeasurementMethod,
            ResultProperty, SourceEvidence,
        )

        # Demote previous canonical records
        self.db.execute(
            ExtractionRecord.__table__.update()
            .where(ExtractionRecord.paper_id == paper.id)
            .where(ExtractionRecord.is_canonical == True)
            .values(is_canonical=False)
        )

        record = ExtractionRecord(
            paper_id=paper.id,
            schema_version=schema_version,
            llm_model=llm_model,
            is_canonical=True,
            status=ExtractionStatus.COMPLETE,
            summary_text=extraction_output.summary,
            raw_llm_response=extraction_output.model_dump(),
            bibliographic_info=extraction_output.bibliographic_info.model_dump() if extraction_output.bibliographic_info else None,
            journal_quality=extraction_output.journal_quality.model_dump() if extraction_output.journal_quality else None,
            main_findings=extraction_output.outcome.main_findings if extraction_output.outcome else None,
            claimed_mechanism=extraction_output.outcome.claimed_mechanism if extraction_output.outcome else None,
            limitations=extraction_output.outcome.limitations if extraction_output.outcome else None,
            notable_novelty=extraction_output.outcome.notable_novelty if extraction_output.outcome else None,
            relevant_for_optimization=extraction_output.outcome.relevant_for_optimization if extraction_output.outcome else None,
            input_variables=extraction_output.input_variables,
            output_variables=extraction_output.output_variables,
            contextual_notes=extraction_output.contextual_notes,
        )

        if extraction_output.fields_needing_review:
            record.status = ExtractionStatus.NEEDS_REVIEW

        self.db.add(record)
        self.db.flush()

        # Materials
        for mat_schema in extraction_output.materials:
            mat = MaterialEntity(
                extraction_id=record.id,
                name=mat_schema.name,
                composition=mat_schema.composition,
                stoichiometry=mat_schema.stoichiometry,
                dopants=mat_schema.dopants,
                substrate=mat_schema.substrate,
                layer_stack=mat_schema.layer_stack,
                device_structure=mat_schema.device_structure,
                crystal_structure=mat_schema.crystal_structure,
                phase=mat_schema.phase,
                dimensionality=mat_schema.dimensionality,
                morphology=mat_schema.morphology,
                additional_properties=mat_schema.additional_properties,
            )
            self.db.add(mat)
            self.db.flush()

            # Evidence for this material
            if mat_schema.evidence:
                ev = mat_schema.evidence
                self.db.add(SourceEvidence(
                    extraction_id=record.id,
                    field_name=f"material.{mat_schema.name or 'unknown'}",
                    field_value=mat_schema.composition,
                    source_text=ev.source_text,
                    page_numbers=ev.page_numbers,
                    section=ev.section,
                    confidence=ev.confidence,
                    is_inferred=ev.is_inferred,
                    inference_reasoning=ev.inference_reasoning,
                ))

        # Process conditions
        for cond in extraction_output.process_conditions:
            self.db.add(ProcessCondition(
                extraction_id=record.id,
                parameter_name=cond.parameter_name,
                value_numeric=cond.value_numeric,
                value_text=cond.value_text,
                unit=cond.unit,
                variable_role=cond.variable_role,
                confidence=cond.confidence,
                is_inferred=cond.is_inferred,
                notes=cond.notes,
            ))
            if cond.evidence:
                ev = cond.evidence
                self.db.add(SourceEvidence(
                    extraction_id=record.id,
                    field_name=f"process_condition.{cond.parameter_name}",
                    field_value=str(cond.value_numeric or cond.value_text),
                    source_text=ev.source_text,
                    page_numbers=ev.page_numbers,
                    section=ev.section,
                    confidence=ev.confidence,
                    is_inferred=ev.is_inferred,
                ))

        # Measurement methods
        for method in extraction_output.measurement_methods:
            self.db.add(MeasurementMethod(
                extraction_id=record.id,
                technique_name=method.technique_name,
                category=method.category,
                description=method.description,
            ))

        # Result properties
        for rp in extraction_output.result_properties:
            self.db.add(ResultProperty(
                extraction_id=record.id,
                property_name=rp.property_name,
                value_numeric=rp.value_numeric,
                value_min=rp.value_min,
                value_max=rp.value_max,
                value_text=rp.value_text,
                unit=rp.unit,
                conditions=rp.conditions,
                variable_role=rp.variable_role,
                confidence=rp.confidence,
                is_inferred=rp.is_inferred,
                needs_review=rp.needs_review,
            ))
            if rp.evidence:
                ev = rp.evidence
                self.db.add(SourceEvidence(
                    extraction_id=record.id,
                    field_name=f"result.{rp.property_name}",
                    field_value=str(rp.value_numeric or rp.value_text),
                    source_text=ev.source_text,
                    page_numbers=ev.page_numbers,
                    section=ev.section,
                    confidence=ev.confidence,
                    is_inferred=ev.is_inferred,
                ))

        # Update paper with paths
        if summary_path:
            paper.summary_path = summary_path
        if extraction_json_path:
            paper.extraction_json_path = extraction_json_path
        paper.schema_version = schema_version
        paper.status = PaperStatus.EXTRACTED

        self.db.flush()
        log.info(
            "Extraction saved",
            paper_id=str(paper.id),
            record_id=str(record.id),
            materials=len(extraction_output.materials),
            conditions=len(extraction_output.process_conditions),
            results=len(extraction_output.result_properties),
        )
        return record

    # ── Job tracking ───────────────────────────────────────────────────────────

    def create_job(
        self,
        job_type: JobType,
        paper: Optional[Paper] = None,
        celery_task_id: Optional[str] = None,
    ) -> ProcessingJob:
        job = ProcessingJob(
            paper_id=paper.id if paper else None,
            job_type=job_type,
            status=JobStatus.QUEUED,
            celery_task_id=celery_task_id,
        )
        self.db.add(job)
        self.db.flush()
        return job

    def get_canonical_extraction(
        self, paper_id: uuid.UUID
    ) -> Optional[ExtractionRecord]:
        return self.db.execute(
            select(ExtractionRecord)
            .where(
                ExtractionRecord.paper_id == paper_id,
                ExtractionRecord.is_canonical == True,
            )
            .options(
                selectinload(ExtractionRecord.materials),
                selectinload(ExtractionRecord.process_conditions),
                selectinload(ExtractionRecord.measurement_methods),
                selectinload(ExtractionRecord.result_properties),
                selectinload(ExtractionRecord.source_evidences),
            )
        ).scalar_one_or_none()
