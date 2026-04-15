"""
Simple key-value settings stored in SQLite.
Avoids the need for a separate config file for user preferences.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings


def get_setting(db: Session, key: str) -> Optional[str]:
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    return row.value if row else None


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSettings(key=key, value=value))
    db.commit()


def get_all_settings(db: Session) -> dict[str, str]:
    rows = db.query(AppSettings).all()
    return {r.key: r.value for r in rows if r.value is not None}
