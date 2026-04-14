"""
Pydantic schemas for extraction records AND the validated LLM output schema.

The LLMExtractionOutput class is the ground truth schema we expect the LLM to return.
It is validated using Pydantic – malformed LLM output will be caught and handled gracefully.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── LLM Output Schema (validated) ─────────────────────────────────────────────

class SourceEvidenceSchema(BaseModel):
    """Provenance for a single extracted field."""
    source_text: Optional[str] = Field(None, description="Direct quote from the paper")
    page_numbers: Optional[List[int]] = Field(None, description="PDF page numbers")
    section: Optional[str] = Field(None, description="Paper section (Abstract, Methods, etc.)")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_inferred: bool = False
    inference_reasoning: Optional[str] = None


class BiblioInfo(BaseModel):
    title: Optional[str] = None
    journal: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = Field(None, ge=1900, le=2100)
    doi: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    keywords: Optional[List[str]] = None
    abstract: Optional[str] = None
    evidence: Optional[SourceEvidenceSchema] = None


class JournalQualitySchema(BaseModel):
    impact_factor: Optional[float] = None
    impact_factor_year: Optional[int] = None
    impact_factor_source: Optional[str] = None
    # "resolved" | "unresolved" – NEVER hallucinate IF
    impact_factor_status: str = "unresolved"
    notes: Optional[str] = None


class MaterialEntitySchema(BaseModel):
    name: Optional[str] = None
    composition: Optional[str] = None
    stoichiometry: Optional[str] = None
    dopants: Optional[List[str]] = None
    substrate: Optional[str] = None
    layer_stack: Optional[str] = None
    device_structure: Optional[str] = None
    crystal_structure: Optional[str] = None
    phase: Optional[str] = None
    dimensionality: Optional[str] = None
    morphology: Optional[str] = None
    additional_properties: Optional[Dict[str, Any]] = None
    evidence: Optional[SourceEvidenceSchema] = None


class ProcessConditionSchema(BaseModel):
    """
    A fabrication/processing parameter.
    [BO-READY] These are the controllable input variables X.
    """
    parameter_name: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    variable_role: str = Field("input", pattern="^(input|output|contextual)$")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_inferred: bool = False
    notes: Optional[str] = None
    evidence: Optional[SourceEvidenceSchema] = None


class MeasurementMethodSchema(BaseModel):
    technique_name: str
    category: Optional[str] = None
    description: Optional[str] = None


class ResultPropertySchema(BaseModel):
    """
    A single experimental result/measurement.
    [BO-READY] These are the optimization target variables y.
    """
    property_name: str
    value_numeric: Optional[float] = None
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    conditions: Optional[str] = None
    variable_role: str = Field("output", pattern="^(input|output|contextual)$")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_inferred: bool = False
    needs_review: bool = False
    evidence: Optional[SourceEvidenceSchema] = None


class OutcomeSchema(BaseModel):
    main_findings: Optional[str] = None
    claimed_mechanism: Optional[str] = None
    limitations: Optional[str] = None
    notable_novelty: Optional[str] = None
    relevant_for_optimization: Optional[bool] = None
    evidence: Optional[SourceEvidenceSchema] = None


class LLMExtractionOutput(BaseModel):
    """
    The validated schema that the LLM must return.
    If any field is uncertain/missing, it should be None or flagged for review.
    This model is the contract between the LLM extraction prompt and the pipeline.

    [BO-READY] The split into input_variables / output_variables / contextual_notes
    directly maps to the X / y / context split needed for Bayesian optimization.
    """
    schema_version: str = "1.0.0"
    summary: str = Field(..., description="Concise human-readable summary of the paper")

    bibliographic_info: Optional[BiblioInfo] = None
    journal_quality: Optional[JournalQualitySchema] = None
    materials: List[MaterialEntitySchema] = Field(default_factory=list)
    process_conditions: List[ProcessConditionSchema] = Field(default_factory=list)
    measurement_methods: List[MeasurementMethodSchema] = Field(default_factory=list)
    result_properties: List[ResultPropertySchema] = Field(default_factory=list)
    outcome: Optional[OutcomeSchema] = None

    # [BO-READY] Explicit variable classification for optimization
    input_variables: Optional[Dict[str, Any]] = Field(
        None,
        description="Controllable process parameters as {name: {value, unit, role}}"
    )
    output_variables: Optional[Dict[str, Any]] = Field(
        None,
        description="Measured performance metrics as {name: {value, unit, role}}"
    )
    contextual_notes: Optional[Dict[str, Any]] = Field(
        None,
        description="Non-controllable context variables"
    )

    # Extraction metadata
    extraction_warnings: List[str] = Field(default_factory=list)
    fields_needing_review: List[str] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Summary cannot be empty")
        return v.strip()


# ── API Response Schemas ───────────────────────────────────────────────────────

class SourceEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    field_name: str
    field_value: Optional[str] = None
    source_text: Optional[str] = None
    page_numbers: Optional[List[int]] = None
    section: Optional[str] = None
    confidence: Optional[float] = None
    is_inferred: bool = False
    inference_reasoning: Optional[str] = None


class MaterialEntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: Optional[str] = None
    composition: Optional[str] = None
    stoichiometry: Optional[str] = None
    dopants: Optional[List[str]] = None
    substrate: Optional[str] = None
    layer_stack: Optional[str] = None
    device_structure: Optional[str] = None
    crystal_structure: Optional[str] = None
    phase: Optional[str] = None
    dimensionality: Optional[str] = None
    morphology: Optional[str] = None
    additional_properties: Optional[Dict[str, Any]] = None


class ProcessConditionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    parameter_name: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    variable_role: str
    confidence: Optional[float] = None
    is_inferred: bool = False
    notes: Optional[str] = None


class MeasurementMethodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    technique_name: str
    category: Optional[str] = None
    description: Optional[str] = None


class ResultPropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    property_name: str
    value_numeric: Optional[float] = None
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    conditions: Optional[str] = None
    variable_role: str
    confidence: Optional[float] = None
    is_inferred: bool = False
    needs_review: bool = False


class ExtractionRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    paper_id: uuid.UUID
    schema_version: str
    llm_model: Optional[str] = None
    is_canonical: bool = True
    status: str
    summary_text: Optional[str] = None
    main_findings: Optional[str] = None
    claimed_mechanism: Optional[str] = None
    limitations: Optional[str] = None
    notable_novelty: Optional[str] = None
    relevant_for_optimization: Optional[bool] = None
    bibliographic_info: Optional[Dict[str, Any]] = None
    journal_quality: Optional[Dict[str, Any]] = None
    input_variables: Optional[Dict[str, Any]] = None
    output_variables: Optional[Dict[str, Any]] = None
    contextual_notes: Optional[Dict[str, Any]] = None
    materials: List[MaterialEntityRead] = []
    process_conditions: List[ProcessConditionRead] = []
    measurement_methods: List[MeasurementMethodRead] = []
    result_properties: List[ResultPropertyRead] = []
    source_evidences: List[SourceEvidenceRead] = []
    human_edited: bool = False
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ExtractionRecordUpdate(BaseModel):
    """For manual human corrections to an extraction record."""
    summary_text: Optional[str] = None
    main_findings: Optional[str] = None
    claimed_mechanism: Optional[str] = None
    limitations: Optional[str] = None
    notable_novelty: Optional[str] = None
    relevant_for_optimization: Optional[bool] = None
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    input_variables: Optional[Dict[str, Any]] = None
    output_variables: Optional[Dict[str, Any]] = None
    contextual_notes: Optional[Dict[str, Any]] = None
