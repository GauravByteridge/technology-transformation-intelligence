"""
ExecutiveBrief and BriefSource ORM models for App_DB.

Executive Briefs are AI-generated project summaries backed by
evidence from queries. BriefSources link a brief to the
evidence and queries that informed its content.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class ExecutiveBrief(AppBase):
    """AI-generated executive brief for a project."""

    __tablename__ = "executive_briefs"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(
        sa.String(500), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    content: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    generated_by_query: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("queries.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="DRAFT"
    )
    created_by: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    sources: Mapped[list["BriefSource"]] = relationship(
        "BriefSource", back_populates="brief", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ExecutiveBrief id={self.id} title={self.title}>"


class BriefSource(AppBase):
    """Links an executive brief to its evidence/query sources."""

    __tablename__ = "brief_sources"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    brief_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("executive_briefs.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )
    query_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("queries.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    brief: Mapped["ExecutiveBrief"] = relationship(
        "ExecutiveBrief", back_populates="sources"
    )

    def __repr__(self) -> str:
        return f"<BriefSource id={self.id} brief={self.brief_id}>"
