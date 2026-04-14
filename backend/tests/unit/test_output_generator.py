"""Unit tests for the output file generator."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.extraction import LLMExtractionOutput
from tests.unit.test_llm_extractor import VALID_EXTRACTION_JSON


class TestOutputGenerator:
    def setup_method(self, tmp_path=None):
        """Set up a temporary directory and mock storage."""
        self.paper_id = uuid.uuid4()

    def test_summary_generation(self, tmp_path):
        """Test that summary.md is generated correctly."""
        from app.services.output_generator import OutputGenerator

        with patch("app.services.output_generator.get_storage") as mock_storage:
            storage_instance = MagicMock()
            summary_path = tmp_path / "summary.md"
            storage_instance.summary_path.return_value = summary_path
            extraction_path = tmp_path / "extraction.json"
            storage_instance.extraction_json_path.return_value = extraction_path
            mock_storage.return_value = storage_instance

            gen = OutputGenerator()
            extraction = LLMExtractionOutput.model_validate(VALID_EXTRACTION_JSON)
            paper_mock = MagicMock()
            paper_mock.original_filename = "test_paper.pdf"

            result_path = gen.generate_summary(paper_mock, extraction, self.paper_id)

            assert summary_path.exists()
            content = summary_path.read_text()
            # Key sections should be present
            assert "TMR" in content
            assert "CoFeB" in content
            assert "350" in content  # annealing temperature
            assert "600" in content  # TMR ratio

    def test_extraction_json_generation(self, tmp_path):
        """Test that extraction.json is valid JSON with correct structure."""
        from app.services.output_generator import OutputGenerator

        with patch("app.services.output_generator.get_storage") as mock_storage:
            storage_instance = MagicMock()
            extraction_path = tmp_path / "extraction.json"
            storage_instance.extraction_json_path.return_value = extraction_path
            mock_storage.return_value = storage_instance

            gen = OutputGenerator()
            extraction = LLMExtractionOutput.model_validate(VALID_EXTRACTION_JSON)

            gen.generate_extraction_json(extraction, self.paper_id)

            assert extraction_path.exists()
            data = json.loads(extraction_path.read_text())
            assert "paper_id" in data
            assert "extraction" in data
            assert data["paper_id"] == str(self.paper_id)
            assert "result_properties" in data["extraction"]
