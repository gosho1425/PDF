"""
Scan endpoints — synchronous for MVP simplicity.
POST /api/scan   → runs folder scan, returns results (blocking)
GET  /api/scan/status → last scan result (stored in DB settings)
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.scanner import run_scan
from app.services.settings_service import get_setting, set_setting

router = APIRouter()
log = logging.getLogger(__name__)

# In-process scan state — for MVP this is sufficient (no Redis/Celery needed)
_scan_state: dict = {"running": False, "last_result": None}


class ScanRequest(BaseModel):
    custom_parameters: Optional[list[dict]] = None


@router.post("")
def trigger_scan(body: ScanRequest, db: Session = Depends(get_db)):
    """
    Run a synchronous folder scan.
    For MVP: blocking call — the frontend should show a loading indicator.
    Response includes a full result summary.
    """
    if _scan_state["running"]:
        raise HTTPException(409, "A scan is already in progress.")

    _scan_state["running"] = True
    try:
        # Load custom parameters from DB if not provided in request
        custom_params = body.custom_parameters
        if custom_params is None:
            raw = get_setting(db, "custom_parameters")
            custom_params = json.loads(raw) if raw else []

        result = run_scan(db, custom_params)

        # Cache last result
        result_dict = {
            "total_found":     result.total_found,
            "new_processed":   result.new_processed,
            "skipped":         result.skipped,
            "failed":          result.failed,
            "errors":          result.errors,
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


@router.get("/status")
def scan_status(db: Session = Depends(get_db)):
    """Return the last scan result and whether a scan is running."""
    raw = get_setting(db, "last_scan_result")
    last = json.loads(raw) if raw else None
    return {
        "running": _scan_state["running"],
        "last_result": last,
    }
