"""
AppDocument ORM model for App_DB.

Represents uploaded document metadata in the application control-plane
database. This is separate from the RAG_DB Document model which handles
embedding and chunk storage. This table tracks document lifecycle,
ownership, and catalog integration.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class AppDocument(AppBase):
    """Uploaded document metadata in the application control-plane."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    data_source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=False
    )
    project_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(
        sa.String(512), nullable=False
    )
    file_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )
    storage_reference: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    file_size: Mapped[int] = mapped_column(
        sa.BigInteger, nullable=False
    )
    checksum: Mapped[str | None] = mapped_column(
        sa.String(128), nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="UPLOADED"
    )
    page_count: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False
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
    data_source: Mapped["DataSource"] = relationship("DataSource")
    project: Mapped["Project | None"] = relationship("Project")

    def __repr__(self) -> str:
        return f"<AppDocument id={self.id} file_name={self.file_name}>"
