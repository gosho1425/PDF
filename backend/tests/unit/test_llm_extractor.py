"""Unit tests for LLM extraction output validation and parsing."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.extraction import LLMExtractionOutput
from app.services.llm_extractor import LLMExtractor, ExtractorError


VALID_EXTRACTION_JSON = {
    "schema_version": "1.0.0",
    "summary": "This paper reports the fabrication of CoFeB/MgO/CoFeB magnetic tunnel junctions with TMR ratios up to 600% at room temperature.",
    "bibliographic_info": {
        "title": "Giant Tunneling Magnetoresistance in CoFeB/MgO/CoFeB Junctions",
        "journal": "Physical Review Letters",
        "authors": ["Zhang, W.", "Smith, J.", "Chen, X."],
        "year": 2022,
        "doi": "10.1103/PhysRevLett.128.107201",
        "volume": "128",
        "issue": "10",
        "pages": "107201",
        "keywords": ["TMR", "magnetic tunnel junction", "spintronics"],
        "abstract": "We report giant TMR in CoFeB/MgO/CoFeB...",
        "evidence": {
            "source_text": "Giant Tunneling Magnetoresistance in CoFeB/MgO/CoFeB Junctions",
            "page_numbers": [1],
            "section": "Header",
            "confidence": 0.95,
            "is_inferred": False
        }
    },
    "journal_quality": {
        "impact_factor": None,
        "impact_factor_year": None,
        "impact_factor_source": None,
        "impact_factor_status": "unresolved",
        "notes": None
    },
    "materials": [
        {
            "name": "CoFeB/MgO/CoFeB MTJ",
            "composition": "Co40Fe40B20 / MgO / Co40Fe40B20",
            "stoichiometry": "Co40Fe40B20",
            "dopants": None,
            "substrate": "SiO2/Si",
            "layer_stack": "Ta(5)/CoFeB(1.8)/MgO(2)/CoFeB(3)/Ta(5) [nm]",
            "device_structure": "magnetic tunnel junction",
            "crystal_structure": "bcc (after annealing)",
            "phase": None,
            "dimensionality": "thin film",
            "morphology": None,
            "additional_properties": {},
            "evidence": {
                "source_text": "the layer structure is Ta(5)/Co40Fe40B20(1.8)/MgO(2)/Co40Fe40B20(3)/Ta(5)",
                "page_numbers": [2],
                "section": "Experimental",
                "confidence": 0.98,
                "is_inferred": False
            }
        }
    ],
    "process_conditions": [
        {
            "parameter_name": "annealing temperature",
            "value_numeric": 350.0,
            "value_text": None,
            "unit": "°C",
            "variable_role": "input",
            "confidence": 0.95,
            "is_inferred": False,
            "notes": None,
            "evidence": {
                "source_text": "annealed at 350 °C for 1 h",
                "page_numbers": [2],
                "section": "Experimental",
                "confidence": 0.95,
                "is_inferred": False
            }
        }
    ],
    "measurement_methods": [
        {
            "technique_name": "Vibrating Sample Magnetometry (VSM)",
            "category": "magnetic",
            "description": "Used to measure M-H hysteresis loops"
        }
    ],
    "result_properties": [
        {
            "property_name": "TMR ratio",
            "value_numeric": 600.0,
            "value_min": None,
            "value_max": None,
            "value_text": None,
            "unit": "%",
            "conditions": "at room temperature, 10 mV bias",
            "variable_role": "output",
            "confidence": 0.97,
            "is_inferred": False,
            "needs_review": False,
            "evidence": {
                "source_text": "we observe a TMR ratio of 600% at room temperature",
                "page_numbers": [3],
                "section": "Results",
                "confidence": 0.97,
                "is_inferred": False
            }
        }
    ],
    "outcome": {
        "main_findings": "CoFeB/MgO/CoFeB junctions show TMR ratios of 600% at RT after 350°C annealing.",
        "claimed_mechanism": "Coherent tunneling through the MgO barrier enhanced by bcc CoFeB crystallization.",
        "limitations": "High TMR only observed at low bias voltages.",
        "notable_novelty": "Highest reported TMR in CoFeB/MgO at room temperature.",
        "relevant_for_optimization": True,
        "evidence": None
    },
    "input_variables": {
        "annealing_temperature": {"value": 350.0, "unit": "°C", "role": "input"}
    },
    "output_variables": {
        "TMR_ratio": {"value": 600.0, "unit": "%", "role": "output"}
    },
    "contextual_notes": {
        "substrate": {"value": "SiO2/Si", "role": "contextual"}
    },
    "extraction_warnings": [],
    "fields_needing_review": []
}


class TestLLMOutputValidation:
    """Tests for the Pydantic validation of LLM output."""

    def test_valid_extraction_parses(self):
        result = LLMExtractionOutput.model_validate(VALID_EXTRACTION_JSON)
        assert result.schema_version == "1.0.0"
        assert "TMR" in result.summary
        assert len(result.materials) == 1
        assert result.materials[0].name == "CoFeB/MgO/CoFeB MTJ"
        assert len(result.process_conditions) == 1
        assert result.process_conditions[0].value_numeric == 350.0
        assert len(result.result_properties) == 1
        assert result.result_properties[0].value_numeric == 600.0

    def test_confidence_bounds_enforced(self):
        bad_data = VALID_EXTRACTION_JSON.copy()
        bad_data = json.loads(json.dumps(bad_data))  # deep copy
        bad_data["result_properties"][0]["confidence"] = 1.5  # > 1.0
        with pytest.raises(Exception):
            LLMExtractionOutput.model_validate(bad_data)

    def test_empty_summary_rejected(self):
        bad_data = {**VALID_EXTRACTION_JSON, "summary": ""}
        with pytest.raises(Exception):
            LLMExtractionOutput.model_validate(bad_data)

    def test_null_fields_acceptable(self):
        """Fields should be null-able, not causing validation errors."""
        minimal = {
            "schema_version": "1.0.0",
            "summary": "Minimal extraction with most fields null.",
            "bibliographic_info": None,
            "journal_quality": None,
            "materials": [],
            "process_conditions": [],
            "measurement_methods": [],
            "result_properties": [],
            "outcome": None,
            "input_variables": None,
            "output_variables": None,
            "contextual_notes": None,
            "extraction_warnings": [],
            "fields_needing_review": ["full_record"]
        }
        result = LLMExtractionOutput.model_validate(minimal)
        assert result.bibliographic_info is None
        assert result.materials == []

    def test_invalid_variable_role_rejected(self):
        bad_data = json.loads(json.dumps(VALID_EXTRACTION_JSON))
        bad_data["process_conditions"][0]["variable_role"] = "banana"
        with pytest.raises(Exception):
            LLMExtractionOutput.model_validate(bad_data)


class TestLLMExtractorParsing:
    """Tests for JSON parsing and recovery in the extractor."""

    def setup_method(self):
        with patch("app.services.llm_extractor.get_settings") as mock_s:
            mock_s.return_value.ANTHROPIC_API_KEY = "test-key"
            mock_s.return_value.ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
            mock_s.return_value.ANTHROPIC_MAX_TOKENS = 8192
            mock_s.return_value.ANTHROPIC_TEMPERATURE = 0.1
            mock_s.return_value.LLM_MAX_CHUNK_CHARS = 60000
            with patch("app.services.llm_extractor.LLMExtractor._load_prompts"):
                self.extractor = LLMExtractor()
                self.extractor._system_prompt = "test system"
                self.extractor._user_template = "test {paper_text}"

    def test_valid_json_parses_correctly(self):
        raw = json.dumps(VALID_EXTRACTION_JSON)
        result = self.extractor._parse_and_validate(raw)
        assert result.result_properties[0].property_name == "TMR ratio"

    def test_json_with_markdown_fences(self):
        raw = f"```json\n{json.dumps(VALID_EXTRACTION_JSON)}\n```"
        result = self.extractor._parse_and_validate(raw)
        assert result is not None
        assert "TMR" in result.summary

    def test_empty_response_raises_extractor_error(self):
        with pytest.raises(ExtractorError, match="empty"):
            self.extractor._parse_and_validate("")

    def test_invalid_json_raises_extractor_error(self):
        with pytest.raises(ExtractorError):
            self.extractor._parse_and_validate("This is not JSON at all.")

    def test_partial_recovery_from_malformed_output(self):
        """Partial recovery should return something rather than nothing."""
        bad_data = {"summary": "Partial result", "materials": None}  # missing required list fields
        result = self.extractor._partial_recovery(bad_data, "test error")
        assert result is not None
        assert result.summary is not None

    def test_merge_deduplicates_materials(self):
        result1 = LLMExtractionOutput.model_validate({
            **VALID_EXTRACTION_JSON,
            "summary": "Part 1"
        })
        result2 = LLMExtractionOutput.model_validate({
            **VALID_EXTRACTION_JSON,
            "summary": "Part 2"
        })
        merged = self.extractor._merge_chunk_results([result1, result2], MagicMock())
        # Materials should be deduplicated by name
        assert len(merged.materials) == 1
