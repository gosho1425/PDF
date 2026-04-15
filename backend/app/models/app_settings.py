"""
App settings stored in SQLite.
Key-value store for user preferences like the paper folder path.
Using the DB means no separate config file; settings survive restarts.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.db.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    key        = Column(String(128), primary_key=True)
    value      = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
