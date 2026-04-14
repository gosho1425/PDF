"""Author and PaperAuthor (association) models."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.paper import Paper


class Author(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authors"

    full_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(256))
    last_name: Mapped[Optional[str]] = mapped_column(String(256))
    orcid: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    affiliation: Mapped[Optional[str]] = mapped_column(String(1024))
    email: Mapped[Optional[str]] = mapped_column(String(256))

    paper_authors: Mapped[list["PaperAuthor"]] = relationship(
        "PaperAuthor", back_populates="author"
    )

    def __repr__(self) -> str:
        return f"<Author name={self.full_name!r}>"


class PaperAuthor(Base):
    """Association table: many papers ↔ many authors with position."""
    __tablename__ = "paper_authors"

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_corresponding: Mapped[bool] = mapped_column(default=False)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="paper_authors")
    author: Mapped["Author"] = relationship("Author", back_populates="paper_authors")
