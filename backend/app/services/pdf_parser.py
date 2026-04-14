"""
PDF parsing service.

Strategy:
1. Try native text extraction with pdfplumber (fast, accurate for digital PDFs).
2. If text quality is below OCR_MIN_TEXT_THRESHOLD, fall back to OCR via tesseract.
3. Return structured ParsedPDF with per-page text and metadata.

This hybrid approach handles:
- Born-digital PDFs (most modern papers): native extraction
- Scanned or image-only PDFs: OCR fallback
- Mixed PDFs: page-by-page decision
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import pdfplumber

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class ParsedPage:
    page_number: int       # 1-indexed
    text: str
    extraction_method: str  # "native" | "ocr"
    word_count: int = 0
    bbox: Optional[tuple] = None


@dataclass
class ParsedPDF:
    pages: List[ParsedPage] = field(default_factory=list)
    total_text: str = ""
    page_count: int = 0
    parse_method: str = "native"  # "native" | "ocr" | "hybrid"
    metadata: dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    # Extracted metadata (best-effort from PDF metadata / first page heuristics)
    title: Optional[str] = None
    doi: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    year: Optional[int] = None


class PDFParser:
    """
    Robust PDF text extractor with OCR fallback.
    """

    DOI_PATTERN = re.compile(
        r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9a-z]+)',
        re.IGNORECASE
    )
    YEAR_PATTERN = re.compile(r'\b(?:19|20)\d{2}\b')  # non-capturing group so findall returns full year

    def __init__(self):
        self.settings = get_settings()
        self._setup_tesseract()

    def _setup_tesseract(self):
        """Configure tesseract path if override is set."""
        if self.settings.TESSERACT_CMD:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = self.settings.TESSERACT_CMD
            except ImportError:
                log.warning("pytesseract not installed; OCR fallback disabled")

    def parse(self, pdf_path: Path) -> ParsedPDF:
        """
        Main entry point: parse a PDF and return structured result.
        """
        log.info("Starting PDF parse", path=str(pdf_path))
        result = ParsedPDF()

        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                result.page_count = len(pdf.pages)
                result.metadata = pdf.metadata or {}

                methods_used = set()
                all_texts: List[str] = []

                for page in pdf.pages:
                    page_num = page.page_number  # 1-indexed in pdfplumber
                    native_text = page.extract_text() or ""
                    word_count = len(native_text.split())

                    if (
                        self.settings.OCR_ENABLED
                        and len(native_text.strip()) < self.settings.OCR_MIN_TEXT_THRESHOLD
                    ):
                        # Try OCR fallback for this page
                        ocr_text = self._ocr_page(page, pdf_path, page_num)
                        if ocr_text and len(ocr_text.strip()) > len(native_text.strip()):
                            parsed_page = ParsedPage(
                                page_number=page_num,
                                text=ocr_text,
                                extraction_method="ocr",
                                word_count=len(ocr_text.split()),
                            )
                            methods_used.add("ocr")
                        else:
                            parsed_page = ParsedPage(
                                page_number=page_num,
                                text=native_text,
                                extraction_method="native",
                                word_count=word_count,
                            )
                            methods_used.add("native")
                    else:
                        parsed_page = ParsedPage(
                            page_number=page_num,
                            text=native_text,
                            extraction_method="native",
                            word_count=word_count,
                        )
                        methods_used.add("native")

                    result.pages.append(parsed_page)
                    all_texts.append(parsed_page.text)

                result.total_text = "\n\n".join(all_texts)
                result.parse_method = (
                    "hybrid" if len(methods_used) > 1
                    else ("ocr" if "ocr" in methods_used else "native")
                )

        except Exception as exc:
            log.error("PDF parsing failed", error=str(exc), path=str(pdf_path))
            result.warnings.append(f"Parse error: {exc}")
            return result

        # Extract metadata heuristics
        result = self._extract_metadata_heuristics(result)

        log.info(
            "PDF parse complete",
            path=str(pdf_path),
            pages=result.page_count,
            method=result.parse_method,
            total_chars=len(result.total_text),
        )
        return result

    def _ocr_page(self, page, pdf_path: Path, page_num: int) -> str:
        """OCR a single page using tesseract via pdf2image."""
        try:
            import pytesseract
            from pdf2image import convert_from_path
            from PIL import Image

            images = convert_from_path(
                str(pdf_path),
                first_page=page_num,
                last_page=page_num,
                dpi=300,
            )
            if not images:
                return ""
            text = pytesseract.image_to_string(images[0], lang="eng")
            log.debug("OCR completed", page=page_num, chars=len(text))
            return text
        except Exception as exc:
            log.warning("OCR failed for page", page=page_num, error=str(exc))
            return ""

    def _extract_metadata_heuristics(self, result: ParsedPDF) -> ParsedPDF:
        """
        Best-effort metadata extraction from PDF text.
        Returns None for fields we cannot confidently determine.
        """
        text = result.total_text
        meta = result.metadata

        # Title: try PDF metadata first, then first non-empty line
        if meta.get("Title"):
            result.title = meta["Title"].strip()
        else:
            first_page_text = result.pages[0].text if result.pages else ""
            lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
            if lines:
                # Heuristic: title is often the first long line (>20 chars, <300 chars)
                for line in lines[:10]:
                    if 20 < len(line) < 300:
                        result.title = line
                        break

        # DOI – strip trailing punctuation that is commonly captured
        doi_matches = self.DOI_PATTERN.findall(text[:5000])  # check first portion
        if doi_matches:
            doi_raw = doi_matches[0]
            result.doi = doi_raw.rstrip('.,;)>')  # clean trailing punctuation

        # Year: look for 4-digit year in metadata or first 2000 chars
        if meta.get("CreationDate"):
            # PDF creation date format: D:YYYYMMDDHHmmSS
            creation = str(meta["CreationDate"])
            year_match = re.search(r'(19|20)\d{2}', creation)
            if year_match:
                y = int(year_match.group())
                if 1990 <= y <= 2030:
                    result.year = y
        if not result.year:
            year_matches = self.YEAR_PATTERN.findall(text[:3000])
            for yr in year_matches:
                y = int(yr)
                if 1990 <= y <= 2030:
                    result.year = y
                    break

        # Abstract: look for "Abstract" keyword
        abstract_match = re.search(
            r'(?:Abstract|ABSTRACT)[:\s]*\n?(.*?)(?:\n\n|\n(?:Keywords|Introduction|1\.))',
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if abstract_match:
            abstract = abstract_match.group(1).strip()
            # Sanity check: real abstract should be 100–3000 chars
            if 100 <= len(abstract) <= 3000:
                result.abstract = abstract

        return result

    def chunk_text(self, text: str, max_chars: int) -> List[str]:
        """
        Split text into chunks for LLM processing.
        Tries to split at paragraph boundaries.
        """
        if len(text) <= max_chars:
            return [text]

        chunks: List[str] = []
        paragraphs = re.split(r'\n{2,}', text)
        current_chunk: List[str] = []
        current_len = 0

        for para in paragraphs:
            if current_len + len(para) > max_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_len = len(para)
            else:
                current_chunk.append(para)
                current_len += len(para)

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        log.debug("Text chunked", total_chars=len(text), num_chunks=len(chunks))
        return chunks


_parser: Optional[PDFParser] = None


def get_pdf_parser() -> PDFParser:
    global _parser
    if _parser is None:
        _parser = PDFParser()
    return _parser
