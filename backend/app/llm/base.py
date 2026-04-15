"""
Abstract base for LLM providers.
Any provider (Anthropic, OpenAI, Gemini) must implement extract().
The extraction schema is provider-independent — same input/output contract.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FieldValue:
    """
    A single extracted field with provenance.
    For Bayesian optimization, every measurement needs a value, unit, and
    confidence so the optimizer can weight uncertain observations.
    """
    value: Any                        # str | float | int | list | None
    unit: Optional[str] = None        # e.g. "K", "A/cm²", "nm", "Pa"
    evidence: Optional[str] = None    # verbatim excerpt from the paper
    page: Optional[int] = None        # page number in the PDF
    confidence: float = 1.0          # 0.0 – 1.0


@dataclass
class ExtractionResult:
    """
    Full structured result returned by every LLM provider.

    input_variables  — things the researcher controls (deposition params, etc.)
    output_variables — things that are measured (Tc, Jc, roughness, etc.)
    material_info    — what material / structure was studied
    bibliographic    — title, authors, journal, year, DOI, IF
    raw_summary      — free-text summary of the paper
    custom_fields    — any extra fields extracted per user config
    """
    # Bibliographic
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    impact_factor: Optional[float] = None

    # Material / structure context
    material_info: dict[str, FieldValue] = field(default_factory=dict)

    # Separated for Bayesian optimization
    input_variables: dict[str, FieldValue] = field(default_factory=dict)
    output_variables: dict[str, FieldValue] = field(default_factory=dict)

    # Free-form summary
    raw_summary: str = ""

    # Any extra fields extracted from custom_parameters config
    custom_fields: dict[str, FieldValue] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict for storage."""
        def _fv(fv: FieldValue) -> dict:
            return {
                "value": fv.value,
                "unit": fv.unit,
                "evidence": fv.evidence,
                "page": fv.page,
                "confidence": fv.confidence,
            }
        return {
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "year": self.year,
            "doi": self.doi,
            "abstract": self.abstract,
            "impact_factor": self.impact_factor,
            "material_info": {k: _fv(v) for k, v in self.material_info.items()},
            "input_variables": {k: _fv(v) for k, v in self.input_variables.items()},
            "output_variables": {k: _fv(v) for k, v in self.output_variables.items()},
            "raw_summary": self.raw_summary,
            "custom_fields": {k: _fv(v) for k, v in self.custom_fields.items()},
        }


class LLMProvider(ABC):
    """Abstract base — implement this to add a new LLM backend."""

    @abstractmethod
    def extract(
        self,
        text: str,
        custom_parameters: list[dict],
    ) -> ExtractionResult:
        """
        Extract structured information from paper text.

        Args:
            text: Full extracted text of the PDF.
            custom_parameters: List of parameter dicts, each with:
                {
                  "name": str,          # e.g. "deposition_temperature"
                  "label": str,         # e.g. "Deposition Temperature"
                  "unit": str,          # e.g. "°C"
                  "role": "input"|"output"|"material",
                  "description": str,   # context for the LLM
                }

        Returns:
            ExtractionResult with all populated fields.
        """
        ...
