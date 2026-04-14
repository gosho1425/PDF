"""
Storage abstraction layer.
Currently implements local filesystem storage.
Designed to be swapped for S3/object storage by replacing this module.

All paths returned are RELATIVE to DATA_DIR so they remain portable.
"""
from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO, Optional

import aiofiles

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class StorageService:
    """
    Local file storage for papers and generated outputs.
    Drop-in replacement pattern: subclass or replace with S3StorageService.
    """

    def __init__(self):
        self.settings = get_settings()
        self.settings.ensure_dirs()

    def paper_dir(self, paper_id: uuid.UUID) -> Path:
        """Return the directory for a specific paper."""
        d = self.settings.PAPERS_DIR / str(paper_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def original_pdf_path(self, paper_id: uuid.UUID) -> Path:
        return self.paper_dir(paper_id) / "original.pdf"

    def summary_path(self, paper_id: uuid.UUID) -> Path:
        return self.paper_dir(paper_id) / "summary.md"

    def extraction_json_path(self, paper_id: uuid.UUID) -> Path:
        return self.paper_dir(paper_id) / "extraction.json"

    def relative_path(self, absolute: Path) -> str:
        """Convert absolute path to relative path string (from DATA_DIR)."""
        return str(absolute.relative_to(self.settings.DATA_DIR))

    async def save_upload(
        self,
        file_obj: BinaryIO,
        paper_id: uuid.UUID,
        original_filename: str,
    ) -> tuple[Path, str, int]:
        """
        Save an uploaded PDF file.
        Returns (absolute_path, sha256_hash, file_size_bytes).
        """
        dest = self.original_pdf_path(paper_id)
        hasher = hashlib.sha256()
        total_bytes = 0

        async with aiofiles.open(dest, "wb") as out:
            while chunk := await file_obj.read(65536):
                hasher.update(chunk)
                total_bytes += len(chunk)
                await out.write(chunk)

        sha256 = hasher.hexdigest()
        log.info(
            "Saved uploaded PDF",
            paper_id=str(paper_id),
            path=str(dest),
            size=total_bytes,
            sha256=sha256,
        )
        return dest, sha256, total_bytes

    def copy_from_folder(
        self, source: Path, paper_id: uuid.UUID
    ) -> tuple[Path, str, int]:
        """
        Copy a PDF from a local folder scan into managed storage.
        Returns (dest_path, sha256, size).
        """
        dest = self.original_pdf_path(paper_id)
        shutil.copy2(source, dest)

        # Compute hash
        hasher = hashlib.sha256()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        size = dest.stat().st_size
        return dest, hasher.hexdigest(), size

    async def write_text(self, path: Path, content: str) -> None:
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(content)

    async def write_bytes(self, path: Path, content: bytes) -> None:
        async with aiofiles.open(path, "wb") as f:
            await f.write(content)

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()

    def exists(self, path: Path) -> bool:
        return path.exists()

    def get_absolute(self, relative: str) -> Path:
        """Convert a stored relative path back to an absolute path."""
        return self.settings.DATA_DIR / relative


_storage_service: Optional[StorageService] = None


def get_storage() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
