"""
CatalogEntry ORM model for App_DB.

CatalogEntries represent discovered data objects (tables, views, collections)
from connected data sources, enriched with semantic metadata for cross-source
intelligence and natural language querying.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class CatalogEntry(AppBase):
    """Enterprise data catalog entry with technical and semantic metadata."""

    __tablename__ = "catalog_entries"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=False
    )

    # Technical metadata
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
    fields: Mapped[dict] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    primary_keys: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=sa.text("'[]'::jsonb"),
    )
    foreign_keys: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=sa.text("'[]'::jsonb"),
    )
    indexes: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=sa.text("'[]'::jsonb"),
    )

    # Semantic metadata
    semantic_name: Mapped[str | None] = mapped_column(
        sa.String(500), nullable=True
    )
    semantic_description: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )
    domain_tags: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=sa.text("'[]'::jsonb"),
    )
    query_capabilities: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=sa.text("'[]'::jsonb"),
    )
    suggested_queries: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=sa.text("'[]'::jsonb"),
    )
    confidence: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, server_default=sa.text("'medium'")
    )
    project_fields: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=sa.text("'[]'::jsonb"),
    )

    # Versioning
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
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    # Relationships
    data_source: Mapped["DataSource"] = relationship(
        "DataSource", back_populates="catalog_entries", lazy="selectin"
    )
    project_source_mappings: Mapped[list["ProjectSourceMapping"]] = relationship(
        "ProjectSourceMapping", back_populates="catalog_entry", lazy="selectin"
    )

    # Table-level constraints
    __table_args__ = (
        sa.UniqueConstraint(
            "source_id",
            "object_name",
            "version",
            name="uq_catalog_entries_source_object_version",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CatalogEntry id={self.id} object_name={self.object_name} "
            f"type={self.object_type}>"
        )
