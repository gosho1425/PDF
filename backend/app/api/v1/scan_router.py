"""
Scan endpoints — synchronous for MVP simplicity.

POST /api/scan                  -> run folder scan for new PDFs
POST /api/scan/reprocess-failed -> re-run only failed papers
GET  /api/scan/status           -> last scan result
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.scanner import run_scan
from app.services.settings_service import get_setting, set_setting

router = APIRouter()
log = logging.getLogger(__name__)

# In-process scan state — sufficient for single-user local MVP
_scan_state: dict = {"running": False, "last_result": None}


class ScanRequest(BaseModel):
    custom_parameters: Optional[list[dict]] = None
    reprocess_failed: bool = False


def _do_scan(db: Session, body: ScanRequest) -> dict:
    """Shared scan logic used by both scan endpoints."""
    if _scan_state["running"]:
        raise HTTPException(409, "A scan is already in progress.")

    _scan_state["running"] = True
    try:
        custom_params = body.custom_parameters
        if custom_params is None:
            raw = get_setting(db, "custom_parameters")
            custom_params = json.loads(raw) if raw else []

        result = run_scan(
            db,
            custom_params,
            reprocess_failed=body.reprocess_failed,
        )

        result_dict = {
            "total_found":      result.total_found,
            "new_processed":    result.new_processed,
            "skipped":          result.skipped,
            "failed":           result.failed,
            "errors":           result.errors,
            "duration_seconds": result.duration_seconds,
        }
        set_setting(db, "last_scan_result", json.dumps(result_dict))
        _scan_state["last_result"] = result_dict
        return result_dict

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.error(f"Scan failed: {e}", exc_info=True)
        raise HTTPException(500, f"Scan error: {e}")
    finally:
        _scan_state["running"] = False


@router.post("")
def trigger_scan(body: ScanRequest, db: Session = Depends(get_db)):
    """
    Run a folder scan.
    - Skips papers already processed successfully (status=done).
    - Skips previously failed papers unless reprocess_failed=true.
    - Returns a full result summary.
    """
    return _do_scan(db, body)


@router.post("/reprocess-failed")
def reprocess_failed_papers(db: Session = Depends(get_db)):
    """
    Re-run LLM extraction on all papers that previously failed.
    Skips papers that are already done.
    """
    body = ScanRequest(reprocess_failed=True)
    return _do_scan(db, body)


@router.get("/status")
def scan_status(db: Session = Depends(get_db)):
    """Return whether a scan is running and the last scan result."""
    raw = get_setting(db, "last_scan_result")
    last = json.loads(raw) if raw else None
    return {
        "running": _scan_state["running"],
        "last_result": last,
    }
