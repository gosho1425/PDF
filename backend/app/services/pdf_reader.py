"""
PDF text extraction.
Uses pdfplumber as primary, falls back to PyMuPDF (fitz) if available.
Both are pure-Python friendly on Windows — no Tesseract required for MVP.
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def extract_text(pdf_path: Path) -> str:
    """
    Extract all text from a PDF file.
    Returns concatenated page text separated by form-feeds.
    Raises on unreadable files.
    """
    text = _try_pdfplumber(pdf_path)
    if text and len(text.strip()) > 100:
        return text

    log.info(f"pdfplumber returned little text for {pdf_path.name}; trying PyMuPDF")
    text2 = _try_pymupdf(pdf_path)
    if text2 and len(text2.strip()) > 100:
        return text2

    if text:
        return text  # return whatever we got

    raise ValueError(f"Could not extract readable text from {pdf_path.name}. "
                     "The file may be scanned/image-only. OCR is not enabled in MVP.")


def _try_pdfplumber(pdf_path: Path) -> str:
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                pages.append(t)
        return "\f".join(pages)
    except Exception as e:
        log.warning(f"pdfplumber failed on {pdf_path.name}: {e}")
        return ""


def _try_pymupdf(pdf_path: Path) -> str:
    try:
        import fitz  # PyMuPDF
        pages = []
        with fitz.open(str(pdf_path)) as doc:
            for page in doc:
                pages.append(page.get_text())
        return "\f".join(pages)
    except ImportError:
        log.debug("PyMuPDF not installed — skipping fallback")
        return ""
    except Exception as e:
        log.warning(f"PyMuPDF failed on {pdf_path.name}: {e}")
        return ""
