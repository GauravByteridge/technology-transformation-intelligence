"""
Conversation and Message ORM models for App_DB.

Conversations are optionally scoped to a project and owned by a user.
Messages represent the back-and-forth within a conversation.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class Conversation(AppBase):
    """AI conversation optionally scoped to a project."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    mode: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(
        sa.String(100), nullable=True
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
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", lazy="selectin"
    )
    queries: Mapped[list["Query"]] = relationship(
        "Query", back_populates="conversation", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} project_id={self.project_id}>"


class Message(AppBase):
    """Individual message within a conversation."""

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    conversation_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role} seq={self.sequence_number}>"
