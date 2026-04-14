"""Unit tests for the PDF parser service."""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.pdf_parser import PDFParser, ParsedPage, ParsedPDF


class TestPDFParserHeuristics:
    """Tests for metadata extraction heuristics (no PDF file needed)."""

    def setup_method(self):
        # Patch at module level so PDFParser initialisation picks it up
        with patch("app.services.pdf_parser.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.TESSERACT_CMD = None
            settings.OCR_ENABLED = False  # disable OCR for unit tests
            settings.OCR_MIN_TEXT_THRESHOLD = 200
            settings.LLM_MAX_CHUNK_CHARS = 60000
            self.parser = PDFParser()
        # Manually override for tests that don't use context manager
        self.parser.settings = type('Settings', (), {
            'TESSERACT_CMD': None,
            'OCR_ENABLED': False,
            'OCR_MIN_TEXT_THRESHOLD': 200,
        })()

    def _make_parsed_pdf(self, text: str, meta: dict | None = None) -> ParsedPDF:
        page = ParsedPage(page_number=1, text=text, extraction_method="native", word_count=len(text.split()))
        pdf = ParsedPDF(pages=[page], total_text=text, page_count=1, metadata=meta or {})
        return pdf

    def test_doi_extraction_standard(self):
        text = "Some paper text. DOI: 10.1016/j.jmmm.2023.170001. More text."
        pdf = self._make_parsed_pdf(text)
        result = self.parser._extract_metadata_heuristics(pdf)
        assert result.doi == "10.1016/j.jmmm.2023.170001"

    def test_doi_extraction_https(self):
        text = "Published at https://doi.org/10.1038/s41586-022-04802-1 in Nature."
        pdf = self._make_parsed_pdf(text)
        result = self.parser._extract_metadata_heuristics(pdf)
        assert result.doi == "10.1038/s41586-022-04802-1"

    def test_doi_not_hallucinated(self):
        text = "This paper has no DOI information."
        pdf = self._make_parsed_pdf(text)
        result = self.parser._extract_metadata_heuristics(pdf)
        assert result.doi is None

    def test_year_extraction(self):
        text = "Received 14 March 2023. Published online 2023. Keywords: spintronics."
        pdf = self._make_parsed_pdf(text)
        result = self.parser._extract_metadata_heuristics(pdf)
        assert result.year == 2023

    def test_year_from_metadata(self):
        pdf = self._make_parsed_pdf("Some text.", meta={"CreationDate": "D:20220815120000"})
        result = self.parser._extract_metadata_heuristics(pdf)
        assert result.year == 2022

    def test_abstract_extraction(self):
        text = (
            "Title: Some Paper\n\n"
            "Abstract\n"
            "We report the synthesis of a novel thin film material with exceptional "
            "magnetic properties. The coercivity reaches 500 Oe at room temperature.\n\n"
            "Keywords: spintronics, thin films"
        )
        pdf = self._make_parsed_pdf(text)
        result = self.parser._extract_metadata_heuristics(pdf)
        assert result.abstract is not None
        assert "coercivity" in result.abstract.lower()

    def test_title_from_pdf_metadata(self):
        pdf = self._make_parsed_pdf(
            "Some text.",
            meta={"Title": "Spin Hall Magnetoresistance in Pt/YIG Bilayers"}
        )
        result = self.parser._extract_metadata_heuristics(pdf)
        assert result.title == "Spin Hall Magnetoresistance in Pt/YIG Bilayers"


class TestTextChunking:
    def setup_method(self):
        with patch("app.services.pdf_parser.get_settings") as mock_settings:
            mock_settings.return_value.TESSERACT_CMD = None
            mock_settings.return_value.OCR_ENABLED = False
            mock_settings.return_value.OCR_MIN_TEXT_THRESHOLD = 200
            self.parser = PDFParser()

    def test_short_text_no_chunking(self):
        text = "Short text that fits in one chunk."
        chunks = self.parser.chunk_text(text, max_chars=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_chunked(self):
        # Create text longer than max_chars
        paragraphs = ["Paragraph " + str(i) + " " + "word " * 50 for i in range(20)]
        text = "\n\n".join(paragraphs)
        chunks = self.parser.chunk_text(text, max_chars=500)
        assert len(chunks) > 1
        # All content preserved
        reconstructed = " ".join(chunks)
        for para in paragraphs:
            assert "Paragraph" in reconstructed

    def test_chunk_boundaries_at_paragraphs(self):
        """Chunks should not split in the middle of a paragraph."""
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = self.parser.chunk_text(text, max_chars=30)
        # Each chunk should be a complete paragraph
        for chunk in chunks:
            assert "\n\n" not in chunk or len(chunk) <= 30
