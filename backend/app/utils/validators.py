"""
Input validation utilities.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


def is_valid_doi(doi: str) -> bool:
    """Validate DOI format."""
    pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9a-z]+$'
    return bool(re.match(pattern, doi, re.IGNORECASE))


def sanitize_filename(filename: str) -> str:
    """Remove potentially dangerous characters from filename."""
    # Keep only safe characters
    safe = re.sub(r'[^\w\-. ]', '', filename)
    return safe.strip() or "unnamed"


def is_safe_path(path: Path, base_dir: Path) -> bool:
    """
    Ensure a path is within the expected base directory.
    Prevents path traversal attacks.
    """
    try:
        path.resolve().relative_to(base_dir.resolve())
        return True
    except ValueError:
        return False


def validate_year(year: Optional[int]) -> Optional[int]:
    """Validate publication year is in reasonable range."""
    if year is None:
        return None
    if 1900 <= year <= 2030:
        return year
    return None
