"""
Extraction record API: view and manually edit extraction results.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.models.extraction import ExtractionRecord, ExtractionStatus
from app.schemas.extraction import ExtractionRecordRead, ExtractionRecordUpdate
from app.services.paper_service import PaperService

router = APIRouter()
log = get_logger(__name__)


@router.get("/{paper_id}", response_model=dict)
async def get_extraction(paper_id: uuid.UUID):
    """Get the canonical extraction record for a paper."""
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    with SyncSession() as db:
        service = PaperService(db)
        record = service.get_canonical_extraction(paper_id)
        if not record:
            raise HTTPException(status_code=404, detail="No extraction found for this paper")

        return _serialize_record(record)


@router.patch("/{paper_id}", response_model=dict)
async def update_extraction(paper_id: uuid.UUID, update: ExtractionRecordUpdate):
    """
    Manually update/correct extraction fields.
    Marks the record as human_edited=True for traceability.
    """
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    with SyncSession() as db:
        service = PaperService(db)
        record = service.get_canonical_extraction(paper_id)
        if not record:
            raise HTTPException(status_code=404, detail="No extraction found for this paper")

        for field, value in update.model_dump(exclude_none=True).items():
            setattr(record, field, value)

        record.human_edited = True
        if record.status != ExtractionStatus.NEEDS_REVIEW:
            record.status = ExtractionStatus.COMPLETE

        db.commit()
        return {"extraction_id": str(record.id), "status": "updated"}


@router.get("/{paper_id}/evidence", response_model=dict)
async def get_source_evidence(
    paper_id: uuid.UUID,
    field_name: Optional[str] = Query(None),
):
    """
    Get source evidence (provenance) for an extraction.
    Optionally filter by field name.
    """
    from app.db.base import get_sync_session_factory
    from sqlalchemy import select
    from app.models.extraction import SourceEvidence
    SyncSession = get_sync_session_factory()

    with SyncSession() as db:
        service = PaperService(db)
        record = service.get_canonical_extraction(paper_id)
        if not record:
            raise HTTPException(status_code=404, detail="No extraction found")

        evidences = record.source_evidences
        if field_name:
            evidences = [e for e in evidences if field_name.lower() in e.field_name.lower()]

        return {
            "paper_id": str(paper_id),
            "extraction_id": str(record.id),
            "evidences": [
                {
                    "id": str(e.id),
                    "field_name": e.field_name,
                    "field_value": e.field_value,
                    "source_text": e.source_text,
                    "page_numbers": e.page_numbers,
                    "section": e.section,
                    "confidence": e.confidence,
                    "is_inferred": e.is_inferred,
                    "inference_reasoning": e.inference_reasoning,
                }
                for e in evidences
            ],
        }


def _serialize_record(record: ExtractionRecord) -> dict:
    return {
        "id": str(record.id),
        "paper_id": str(record.paper_id),
        "schema_version": record.schema_version,
        "llm_model": record.llm_model,
        "is_canonical": record.is_canonical,
        "status": record.status.value,
        "summary_text": record.summary_text,
        "main_findings": record.main_findings,
        "claimed_mechanism": record.claimed_mechanism,
        "limitations": record.limitations,
        "notable_novelty": record.notable_novelty,
        "relevant_for_optimization": record.relevant_for_optimization,
        "bibliographic_info": record.bibliographic_info,
        "journal_quality": record.journal_quality,
        "input_variables": record.input_variables,
        "output_variables": record.output_variables,
        "contextual_notes": record.contextual_notes,
        "human_edited": record.human_edited,
        "reviewed_by": record.reviewed_by,
        "review_notes": record.review_notes,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "materials": [
            {
                "id": str(m.id),
                "name": m.name,
                "composition": m.composition,
                "stoichiometry": m.stoichiometry,
                "dopants": m.dopants,
                "substrate": m.substrate,
                "layer_stack": m.layer_stack,
                "device_structure": m.device_structure,
                "crystal_structure": m.crystal_structure,
                "phase": m.phase,
                "dimensionality": m.dimensionality,
                "morphology": m.morphology,
            }
            for m in record.materials
        ],
        "process_conditions": [
            {
                "id": str(c.id),
                "parameter_name": c.parameter_name,
                "value_numeric": c.value_numeric,
                "value_text": c.value_text,
                "unit": c.unit,
                "variable_role": c.variable_role,
                "confidence": c.confidence,
                "is_inferred": c.is_inferred,
                "notes": c.notes,
            }
            for c in record.process_conditions
        ],
        "measurement_methods": [
            {
                "id": str(m.id),
                "technique_name": m.technique_name,
                "category": m.category,
                "description": m.description,
            }
            for m in record.measurement_methods
        ],
        "result_properties": [
            {
                "id": str(r.id),
                "property_name": r.property_name,
                "value_numeric": r.value_numeric,
                "value_min": r.value_min,
                "value_max": r.value_max,
                "value_text": r.value_text,
                "unit": r.unit,
                "conditions": r.conditions,
                "variable_role": r.variable_role,
                "confidence": r.confidence,
                "is_inferred": r.is_inferred,
                "needs_review": r.needs_review,
            }
            for r in record.result_properties
        ],
    }
