"""
CatalogField ORM model for App_DB.

Represents individual fields/columns discovered within a catalog entry.
Stores both technical metadata (data type, nullability) and semantic
metadata (semantic type, description) for AI querying.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class CatalogField(AppBase):
    """Field/column within a catalog entry with semantic enrichment."""

    __tablename__ = "catalog_fields"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    catalog_entry_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_entries.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(
        sa.String(255), nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    data_type: Mapped[str] = mapped_column(
        sa.String(100), nullable=False
    )
    semantic_type: Mapped[str | None] = mapped_column(
        sa.String(100), nullable=True
    )
    description: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    nullable: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True
    )
    is_identifier: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    is_project_key: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    is_sensitive: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    sample_metadata: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(
        sa.Numeric(5, 4), nullable=True
    )
    ordinal_position: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
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
    catalog_entry: Mapped["CatalogEntry"] = relationship(
        "CatalogEntry", back_populates="catalog_fields"
    )

    def __repr__(self) -> str:
        return f"<CatalogField id={self.id} name={self.field_name}>"
