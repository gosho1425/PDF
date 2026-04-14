"""Journal model with optional impact factor tracking."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.paper import Paper


class Journal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "journals"

    name: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    abbreviation: Mapped[Optional[str]] = mapped_column(String(128))
    issn: Mapped[Optional[str]] = mapped_column(String(32))
    eissn: Mapped[Optional[str]] = mapped_column(String(32))
    publisher: Mapped[Optional[str]] = mapped_column(String(256))

    # Impact Factor – do NOT hallucinate. Only store if explicitly available.
    impact_factor: Mapped[Optional[float]] = mapped_column(Float)
    impact_factor_year: Mapped[Optional[int]] = mapped_column(Integer)
    impact_factor_source: Mapped[Optional[str]] = mapped_column(String(256))
    # "resolved" | "unresolved" | "not_applicable"
    impact_factor_status: Mapped[Optional[str]] = mapped_column(String(32), default="unresolved")

    notes: Mapped[Optional[str]] = mapped_column(Text)

    papers: Mapped[List["Paper"]] = relationship("Paper", back_populates="journal")

    def __repr__(self) -> str:
        return f"<Journal name={self.name!r}>"
