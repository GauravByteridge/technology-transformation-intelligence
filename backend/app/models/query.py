"""
QueryHistory and SavedQuery ORM models for App_DB.

QueryHistory tracks every AI query for traceability and audit.
SavedQueries allow users to bookmark useful questions for reuse.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AppBase


class QueryHistory(AppBase):
    """Record of an AI query execution for traceability."""

    __tablename__ = "query_history"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    query_id: Mapped[UUID] = mapped_column(sa.UUID, nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("conversations.id"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    question: Mapped[str] = mapped_column(sa.Text, nullable=False)
    response: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    tools_invoked: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    sources_consulted: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    is_partial: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    llm_provider: Mapped[str | None] = mapped_column(
        sa.String(100), nullable=True
    )
    llm_model: Mapped[str | None] = mapped_column(
        sa.String(100), nullable=True
    )
    prompt_version: Mapped[str | None] = mapped_column(
        sa.String(50), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True
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

    def __repr__(self) -> str:
        return f"<QueryHistory id={self.id} query_id={self.query_id}>"


class SavedQuery(AppBase):
    """User-saved query for quick reuse."""

    __tablename__ = "saved_queries"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
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
