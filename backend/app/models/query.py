"""
Query and SavedQuery ORM models for App_DB.

The queries table is the primary record of AI query executions per the design spec.
QueryHistory is retained as a backward-compatible alias for Query.
SavedQueries allow users to bookmark useful questions for reuse.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class Query(AppBase):
    """Record of an AI query execution for traceability and history.

    Spec table name: queries
    Replaces the prior 'query_history' table with correct column set.
    """

    __tablename__ = "queries"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    conversation_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="PENDING"
    )
    mode: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(
        sa.String(100), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="queries"
    )

    def __repr__(self) -> str:
        return f"<Query id={self.id} status={self.status}>"


# Backward-compatible alias for existing repository/service code
QueryHistory = Query


class SavedQuery(AppBase):
    """User-saved query for quick reuse."""

    __tablename__ = "saved_queries"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    question: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SavedQuery id={self.id} title={self.title}>"
