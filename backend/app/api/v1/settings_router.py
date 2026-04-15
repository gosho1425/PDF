"""
Settings endpoints.
GET  /api/settings       → return current settings
POST /api/settings       → update one or more settings
GET  /api/settings/llm   → return LLM config (no secret values)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.services.settings_service import get_all_settings, get_setting, set_setting

router = APIRouter()


class SettingsUpdate(BaseModel):
    paper_folder: Optional[str] = None
    custom_parameters: Optional[list[dict]] = None


@router.get("")
def read_settings(db: Session = Depends(get_db)):
    """Return all user-configurable settings."""
    cfg = get_all_settings(db)
    folder = cfg.get("paper_folder", "")

    folder_status = "not_set"
    if folder:
        p = Path(folder)
        if p.exists() and p.is_dir():
            folder_status = "ok"
            pdf_count = sum(1 for _ in p.rglob("*.pdf")) + sum(1 for _ in p.rglob("*.PDF"))
        else:
            folder_status = "not_found"
            pdf_count = 0
    else:
        pdf_count = 0

    return {
        "paper_folder": folder,
        "folder_status": folder_status,   # "not_set" | "ok" | "not_found"
        "pdf_count": pdf_count,
        "custom_parameters": cfg.get("custom_parameters", "[]"),
    }


@router.post("")
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    """Save one or more settings."""
    import json

    if body.paper_folder is not None:
        folder = body.paper_folder.strip()
        set_setting(db, "paper_folder", folder)

    if body.custom_parameters is not None:
        set_setting(db, "custom_parameters", json.dumps(body.custom_parameters))

    return {"status": "saved"}


@router.get("/llm")
def llm_info():
    """Return LLM configuration (no API keys)."""
    s = get_settings()
    return {
        "provider": s.LLM_PROVIDER,
        "model": s.LLM_MODEL,
        "max_tokens": s.LLM_MAX_TOKENS,
        "temperature": s.LLM_TEMPERATURE,
        "timeout_seconds": s.LLM_TIMEOUT_SECONDS,
    }


@router.post("/validate-folder")
def validate_folder(body: dict):
    """Check if a folder path exists and is readable."""
    folder_str = body.get("folder", "").strip()
    if not folder_str:
        raise HTTPException(400, "No folder path provided")
    p = Path(folder_str)
    if not p.exists():
        return {"valid": False, "reason": f"Path does not exist: {folder_str}"}
    if not p.is_dir():
        return {"valid": False, "reason": f"Path is not a directory: {folder_str}"}
    try:
        pdf_count = sum(1 for _ in p.rglob("*.pdf")) + sum(1 for _ in p.rglob("*.PDF"))
    except PermissionError:
        return {"valid": False, "reason": f"Permission denied reading: {folder_str}"}
    return {"valid": True, "pdf_count": pdf_count, "path": str(p.resolve())}
