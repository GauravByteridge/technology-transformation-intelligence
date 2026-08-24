"""
DocumentVersion ORM model for App_DB.

Tracks version history for uploaded documents, enabling re-upload
without losing the previous processing state.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class DocumentVersion(AppBase):
    """Version record for an uploaded document."""

    __tablename__ = "document_versions"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    checksum: Mapped[str] = mapped_column(
        sa.String(128), nullable=False
    )
    storage_reference: Mapped[str] = mapped_column(
        sa.Text, nullable=False
    )
    processing_status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Unique constraint: one version number per document
    __table_args__ = (
        sa.UniqueConstraint(
            "document_id", "version_number",
            name="uq_document_versions_doc_version",
        ),
    )

    def __repr__(self) -> str:
        return f"<DocumentVersion id={self.id} v={self.version_number}>"
