"""
AuditLog ORM model for App_DB.

Tracks significant user and system actions for compliance and debugging.
Each entry includes the acting user, affected entity, and contextual details.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AppBase


class AuditLog(AppBase):
    """Immutable record of a platform action for audit and traceability."""

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(sa.UUID, nullable=True)
    details: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(
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

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} entity_type={self.entity_type}>"
