"""
Extraction models: the core scientific data extracted by the LLM pipeline.

Design principles:
- Use JSONB for flexible sub-schemas (so we don't need 50 columns per paper).
- Use structured rows for things we always want to query (ResultProperty).
- Every important field has a matching SourceEvidence row for provenance.
- The schema is designed for future transformation into X / y feature matrices
  for Bayesian optimization (see comments marked [BO-READY]).
"""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.paper import Paper


class ExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class ExtractionRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Top-level extraction record for a paper.
    One paper may have multiple versions (e.g. re-extraction after schema update).
    The canonical record is marked is_canonical=True.
    """
    __tablename__ = "extraction_records"

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    paper: Mapped["Paper"] = relationship("Paper", back_populates="extraction_records")

    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    llm_model: Mapped[Optional[str]] = mapped_column(String(128))
    llm_prompt_version: Mapped[Optional[str]] = mapped_column(String(32))
    is_canonical: Mapped[bool] = mapped_column(default=True, index=True)
    status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, name="extraction_status"),
        default=ExtractionStatus.PENDING,
    )

    # ── Human-readable summary (also written to summary.txt) ──────────────────
    summary_text: Mapped[Optional[str]] = mapped_column(Text)

    # ── Top-level outcome fields ───────────────────────────────────────────────
    main_findings: Mapped[Optional[str]] = mapped_column(Text)
    claimed_mechanism: Mapped[Optional[str]] = mapped_column(Text)
    limitations: Mapped[Optional[str]] = mapped_column(Text)
    notable_novelty: Mapped[Optional[str]] = mapped_column(Text)
    # [BO-READY] flag papers directly useful for experiment design
    relevant_for_optimization: Mapped[Optional[bool]] = mapped_column(Boolean)

    # ── Flexible JSONB stores for structured but variable sub-records ──────────
    # These mirror the JSON extraction file.  Structured rows live below.
    raw_llm_response: Mapped[Optional[dict]] = mapped_column(JSONB)  # store verbatim LLM output
    bibliographic_info: Mapped[Optional[dict]] = mapped_column(JSONB)
    journal_quality: Mapped[Optional[dict]] = mapped_column(JSONB)
    # [BO-READY] input / output variable classification
    input_variables: Mapped[Optional[dict]] = mapped_column(JSONB)   # controllable process params
    output_variables: Mapped[Optional[dict]] = mapped_column(JSONB)  # measured performance metrics
    contextual_notes: Mapped[Optional[dict]] = mapped_column(JSONB)  # qualitative context

    # ── Structured relationships ───────────────────────────────────────────────
    materials: Mapped[List["MaterialEntity"]] = relationship(
        "MaterialEntity", back_populates="extraction", cascade="all, delete-orphan"
    )
    process_conditions: Mapped[List["ProcessCondition"]] = relationship(
        "ProcessCondition", back_populates="extraction", cascade="all, delete-orphan"
    )
    measurement_methods: Mapped[List["MeasurementMethod"]] = relationship(
        "MeasurementMethod", back_populates="extraction", cascade="all, delete-orphan"
    )
    result_properties: Mapped[List["ResultProperty"]] = relationship(
        "ResultProperty", back_populates="extraction", cascade="all, delete-orphan"
    )
    source_evidences: Mapped[List["SourceEvidence"]] = relationship(
        "SourceEvidence", back_populates="extraction", cascade="all, delete-orphan"
    )

    # ── Review metadata ────────────────────────────────────────────────────────
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(256))
    review_notes: Mapped[Optional[str]] = mapped_column(Text)
    human_edited: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        return f"<ExtractionRecord paper_id={self.paper_id} status={self.status}>"


class MaterialEntity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Represents a material / system described in the paper.
    A paper may study multiple materials.
    [BO-READY] material identity is a key contextual variable.
    """
    __tablename__ = "material_entities"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_records.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    extraction: Mapped["ExtractionRecord"] = relationship(
        "ExtractionRecord", back_populates="materials"
    )

    name: Mapped[Optional[str]] = mapped_column(String(512))
    composition: Mapped[Optional[str]] = mapped_column(String(512))
    stoichiometry: Mapped[Optional[str]] = mapped_column(String(256))
    dopants: Mapped[Optional[list]] = mapped_column(JSONB)        # list[str]
    substrate: Mapped[Optional[str]] = mapped_column(String(256))
    layer_stack: Mapped[Optional[str]] = mapped_column(Text)
    device_structure: Mapped[Optional[str]] = mapped_column(Text)
    crystal_structure: Mapped[Optional[str]] = mapped_column(String(256))
    phase: Mapped[Optional[str]] = mapped_column(String(128))
    dimensionality: Mapped[Optional[str]] = mapped_column(String(128))
    morphology: Mapped[Optional[str]] = mapped_column(String(256))
    additional_properties: Mapped[Optional[dict]] = mapped_column(JSONB)


class ProcessCondition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single fabrication / processing parameter.
    [BO-READY] These become the controllable input variables X.
    """
    __tablename__ = "process_conditions"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_records.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    extraction: Mapped["ExtractionRecord"] = relationship(
        "ExtractionRecord", back_populates="process_conditions"
    )

    parameter_name: Mapped[str] = mapped_column(String(256), nullable=False)
    value_numeric: Mapped[Optional[float]] = mapped_column(Float)
    value_text: Mapped[Optional[str]] = mapped_column(String(512))
    unit: Mapped[Optional[str]] = mapped_column(String(64))
    # [BO-READY] explicitly mark as input / output / contextual
    variable_role: Mapped[str] = mapped_column(
        String(32), default="input"
    )  # "input" | "output" | "contextual"
    confidence: Mapped[Optional[float]] = mapped_column(Float)  # 0.0–1.0
    is_inferred: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class MeasurementMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Characterization / measurement technique used in the paper."""
    __tablename__ = "measurement_methods"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_records.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    extraction: Mapped["ExtractionRecord"] = relationship(
        "ExtractionRecord", back_populates="measurement_methods"
    )

    technique_name: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(128))
    # "structural" | "electrical" | "magnetic" | "optical" | "thermal" | "other"
    description: Mapped[Optional[str]] = mapped_column(Text)


class ResultProperty(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single quantitative or qualitative experimental result.
    [BO-READY] These become the output variables y for optimization targets.
    """
    __tablename__ = "result_properties"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_records.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    extraction: Mapped["ExtractionRecord"] = relationship(
        "ExtractionRecord", back_populates="result_properties"
    )

    property_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    value_numeric: Mapped[Optional[float]] = mapped_column(Float)
    value_min: Mapped[Optional[float]] = mapped_column(Float)
    value_max: Mapped[Optional[float]] = mapped_column(Float)
    value_text: Mapped[Optional[str]] = mapped_column(String(512))
    unit: Mapped[Optional[str]] = mapped_column(String(64))
    conditions: Mapped[Optional[str]] = mapped_column(Text)  # e.g. "at 300 K, in-plane"
    # [BO-READY] role in the optimization problem
    variable_role: Mapped[str] = mapped_column(
        String(32), default="output"
    )  # "input" | "output" | "contextual"
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    is_inferred: Mapped[bool] = mapped_column(default=False)
    needs_review: Mapped[bool] = mapped_column(default=False)
    material_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_entities.id"), nullable=True
    )


class SourceEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Provenance record: links an extracted field to its source in the PDF.
    Critical for auditability and trust.
    """
    __tablename__ = "source_evidences"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_records.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    extraction: Mapped["ExtractionRecord"] = relationship(
        "ExtractionRecord", back_populates="source_evidences"
    )

    # Which field this evidence supports
    field_name: Mapped[str] = mapped_column(String(256), nullable=False)
    field_value: Mapped[Optional[str]] = mapped_column(Text)

    # Provenance
    source_text: Mapped[Optional[str]] = mapped_column(Text)    # exact quote from paper
    page_numbers: Mapped[Optional[list]] = mapped_column(JSONB)  # list[int]
    section: Mapped[Optional[str]] = mapped_column(String(256))  # "Abstract", "Methods", etc.
    confidence: Mapped[Optional[float]] = mapped_column(Float)   # 0.0–1.0 heuristic
    is_inferred: Mapped[bool] = mapped_column(default=False)
    inference_reasoning: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<SourceEvidence field={self.field_name!r} page={self.page_numbers}>"
