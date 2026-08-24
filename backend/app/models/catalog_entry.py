"""
CatalogEntry ORM model for App_DB.

Represents discovered data objects in the unified enterprise catalog.
Each entry corresponds to a table (PostgreSQL) or collection (MongoDB)
discovered during source schema discovery.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class CatalogEntry(AppBase):
    """Enterprise data catalog entry with semantic metadata."""

    __tablename__ = "catalog_entries"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=False
    )
    database_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    schema_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    object_name: Mapped[str] = mapped_column(
        sa.String(255), nullable=False
    )
    object_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )
    fields: Mapped[list] = mapped_column(
        postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
    )
    primary_keys: Mapped[list] = mapped_column(
        postgresql.JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")
    )
    foreign_keys: Mapped[list] = mapped_column(
        postgresql.JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")
    )
    indexes: Mapped[list] = mapped_column(
        postgresql.JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")
    )
    semantic_name: Mapped[str | None] = mapped_column(
        sa.String(500), nullable=True
    )
    semantic_description: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    domain_tags: Mapped[list] = mapped_column(
        postgresql.JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")
    )
    query_capabilities: Mapped[list] = mapped_column(
        postgresql.JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")
    )
    suggested_queries: Mapped[list] = mapped_column(
        postgresql.JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")
    )
    confidence: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, server_default=sa.text("'medium'")
    )
    project_fields: Mapped[list] = mapped_column(
        postgresql.JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")
    )
    version: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("1")
    )
    discovered_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
    )

    # Relationships
    data_source: Mapped["DataSource"] = relationship(
        "DataSource", back_populates="catalog_entries", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<CatalogEntry id={self.id} source_id={self.source_id} object={self.object_name}>"
