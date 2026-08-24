"""
Evidence ORM model for App_DB.

Stores structured evidence retrieved during AI query execution.
Each evidence record links to a specific query source usage and
contains the actual data/excerpt that supports the AI answer.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class Evidence(AppBase):
    """Structured evidence supporting an AI query answer."""

    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    query_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    query_source_usage_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("query_source_usage.id", ondelete="CASCADE"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )
    source_reference: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    content: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    structured_value: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    page_number: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True
    )
    sheet_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    record_reference: Mapped[str | None] = mapped_column(
        sa.String(500), nullable=True
    )
    relevance_score: Mapped[float | None] = mapped_column(
        sa.Numeric(5, 4), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    query: Mapped["Query"] = relationship(
        "Query", back_populates="evidence_items"
    )
    source_usage: Mapped["QuerySourceUsage"] = relationship(
        "QuerySourceUsage"
    )

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} type={self.evidence_type}>"
