"""
LineageRun and LineageNode ORM models for App_DB.

Captures the data lineage graph for each AI query, showing how
the answer was constructed from question → catalog → tools →
data sources → evidence → synthesis → answer.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class LineageRun(AppBase):
    """Top-level lineage graph for a single query execution."""

    __tablename__ = "lineage_runs"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    query_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    query: Mapped["Query"] = relationship(
        "Query", back_populates="lineage_run"
    )
    nodes: Mapped[list["LineageNode"]] = relationship(
        "LineageNode", back_populates="lineage_run", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<LineageRun id={self.id} query={self.query_id}>"


class LineageNode(AppBase):
    """Individual node in the query lineage graph."""

    __tablename__ = "lineage_nodes"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    lineage_run_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("lineage_runs.id", ondelete="CASCADE"), nullable=False
    )
    node_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )
    node_key: Mapped[str] = mapped_column(
        sa.String(255), nullable=False
    )
    label: Mapped[str] = mapped_column(
        sa.String(500), nullable=False
    )
    source_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    catalog_entry_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_entries.id", ondelete="SET NULL"), nullable=True
    )
    tool_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    sequence_number: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    lineage_run: Mapped["LineageRun"] = relationship(
        "LineageRun", back_populates="nodes"
    )

    def __repr__(self) -> str:
        return f"<LineageNode id={self.id} type={self.node_type}>"
