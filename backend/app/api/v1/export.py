"""
Data export endpoints.
Supports CSV and JSON export of extraction results for downstream analysis.
Designed for easy import into Bayesian optimization pipelines.
"""
from __future__ import annotations

import io
import json
import uuid
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.extraction import ExtractionRecord, ResultProperty, ProcessCondition
from app.models.paper import Paper
from app.schemas.export import ExportRequest

router = APIRouter()
log = get_logger(__name__)
settings = get_settings()


@router.post("/papers")
async def export_papers(request: ExportRequest):
    """
    Export selected papers and their extractions.

    Returns a CSV or JSON file containing:
    - Paper metadata
    - Extracted process conditions (input variables)
    - Extracted result properties (output variables)
    - Material information

    [BO-READY] The output is structured for direct use in Bayesian optimization:
      - input_variables → X feature matrix
      - output_variables → y target matrix
    """
    from app.db.base import get_sync_session_factory
    SyncSession = get_sync_session_factory()

    with SyncSession() as db:
        # Build query
        query = (
            select(Paper)
            .options(
                selectinload(Paper.journal),
                selectinload(Paper.extraction_records).selectinload(ExtractionRecord.process_conditions),
                selectinload(Paper.extraction_records).selectinload(ExtractionRecord.result_properties),
                selectinload(Paper.extraction_records).selectinload(ExtractionRecord.materials),
            )
        )
        if request.paper_ids:
            query = query.where(Paper.id.in_(request.paper_ids))

        papers = list(db.execute(query).scalars().all())

    if not papers:
        raise HTTPException(status_code=404, detail="No papers found")

    if request.format == "csv":
        return _export_csv(papers, request)
    elif request.format == "json":
        return _export_json(papers, request)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")


def _export_csv(papers, request: ExportRequest) -> StreamingResponse:
    """
    Export as a flat CSV suitable for pandas / sklearn / BO libraries.
    Each row is one (paper, result_property) pair with corresponding
    process conditions pivoted as columns.
    """
    rows = []

    for paper in papers:
        canonical_extraction = next(
            (r for r in paper.extraction_records if r.is_canonical), None
        )
        if not canonical_extraction:
            continue

        # Base paper metadata
        base = {
            "paper_id": str(paper.id),
            "title": paper.title,
            "doi": paper.doi,
            "year": paper.publication_year,
            "journal": paper.journal.name if paper.journal else None,
            "extraction_status": canonical_extraction.status.value,
        }

        # Process conditions → input columns
        for cond in canonical_extraction.process_conditions:
            if cond.variable_role in ("input", "contextual"):
                col_name = f"input_{cond.parameter_name.lower().replace(' ', '_')}"
                base[col_name] = cond.value_numeric if cond.value_numeric is not None else cond.value_text
                base[f"{col_name}_unit"] = cond.unit
                base[f"{col_name}_confidence"] = cond.confidence

        # Result properties → output columns
        for rp in canonical_extraction.result_properties:
            col_name = f"output_{rp.property_name.lower().replace(' ', '_')}"
            base[col_name] = rp.value_numeric if rp.value_numeric is not None else rp.value_text
            base[f"{col_name}_unit"] = rp.unit
            base[f"{col_name}_needs_review"] = rp.needs_review
            base[f"{col_name}_confidence"] = rp.confidence

        # Material info
        if canonical_extraction.materials:
            mat = canonical_extraction.materials[0]  # primary material
            base["material_name"] = mat.name
            base["material_composition"] = mat.composition
            base["material_substrate"] = mat.substrate
            base["crystal_structure"] = mat.crystal_structure

        rows.append(base)

    if not rows:
        raise HTTPException(status_code=404, detail="No extracted data available for export")

    df = pd.DataFrame(rows)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    filename = f"paperlens_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(csv_buffer.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _export_json(papers, request: ExportRequest) -> StreamingResponse:
    """
    Export as structured JSON for programmatic consumption.
    [BO-READY] Includes explicit X/y separation for optimization.
    """
    export_data = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "schema_version": settings.SCHEMA_VERSION,
        "total_papers": len(papers),
        "papers": [],
    }

    for paper in papers:
        canonical = next(
            (r for r in paper.extraction_records if r.is_canonical), None
        )

        paper_export = {
            "paper_id": str(paper.id),
            "title": paper.title,
            "doi": paper.doi,
            "year": paper.publication_year,
            "journal": paper.journal.name if paper.journal else None,
        }

        if canonical:
            paper_export["extraction"] = {
                "status": canonical.status.value,
                "summary": canonical.summary_text,
                "input_variables": canonical.input_variables or {},
                "output_variables": canonical.output_variables or {},
                "contextual_notes": canonical.contextual_notes or {},
                # [BO-READY] structured for X/y split
                "bo_ready": {
                    "X": {
                        c.parameter_name: {
                            "value": c.value_numeric,
                            "unit": c.unit,
                            "confidence": c.confidence,
                        }
                        for c in canonical.process_conditions
                        if c.variable_role == "input"
                    },
                    "y": {
                        r.property_name: {
                            "value": r.value_numeric,
                            "value_min": r.value_min,
                            "value_max": r.value_max,
                            "unit": r.unit,
                            "conditions": r.conditions,
                            "confidence": r.confidence,
                        }
                        for r in canonical.result_properties
                        if r.variable_role == "output"
                    },
                },
            }
            if request.include_raw_extraction:
                paper_export["extraction"]["raw_llm_response"] = canonical.raw_llm_response

        export_data["papers"].append(paper_export)

    json_bytes = json.dumps(export_data, indent=2, ensure_ascii=False).encode("utf-8")
    filename = f"paperlens_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
