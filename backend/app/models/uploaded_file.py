"""
UploadedFile ORM model for App_DB.

Tracks files uploaded to the platform for document ingestion.
The actual document processing (chunking, embedding) happens in RAG_DB,
but the file metadata and processing status lives in App_DB.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AppBase


class UploadedFile(AppBase):
    """Record of a file uploaded for document ingestion."""

    __tablename__ = "uploaded_files"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    data_source_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    processing_status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="pending"
    )
    processing_error: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    uploaded_by: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
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
        return f"<UploadedFile id={self.id} file_name={self.file_name}>"
