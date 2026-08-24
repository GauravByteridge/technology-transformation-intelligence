"""
QuerySourceUsage ORM model for App_DB.

Tracks which data sources and catalog entries were consulted
during a query execution. Powers the "Sources Consulted" UI
and ensures source attribution is data-driven, not hardcoded.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class QuerySourceUsage(AppBase):
    """Record of a data source consultation during query execution."""

    __tablename__ = "query_source_usage"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    query_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    data_source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    catalog_entry_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_entries.id", ondelete="SET NULL"), nullable=True
    )
    tool_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="success"
    )
    records_retrieved: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    chunks_retrieved: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    duration_ms: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    query: Mapped["Query"] = relationship(
        "Query", back_populates="source_usages"
    )
    data_source: Mapped["DataSource"] = relationship("DataSource")
    catalog_entry: Mapped["CatalogEntry | None"] = relationship("CatalogEntry")

    def __repr__(self) -> str:
        return f"<QuerySourceUsage id={self.id} query={self.query_id}>"
