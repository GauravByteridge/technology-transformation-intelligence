"""
DocumentProcessingRun ORM model for App_DB.

Records each processing execution for a document (parsing, extraction,
chunking, indexing). Enables the UI to show processing pipeline status.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class DocumentProcessingRun(AppBase):
    """Record of a document processing pipeline execution."""

    __tablename__ = "document_processing_runs"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="running"
    )
    parser_type: Mapped[str | None] = mapped_column(
        sa.String(100), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    chunks_created: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    datasets_created: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )

    def __repr__(self) -> str:
        return f"<DocumentProcessingRun id={self.id} status={self.status}>"
