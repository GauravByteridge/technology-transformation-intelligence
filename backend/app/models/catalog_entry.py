"""
CatalogEntry ORM model for App_DB.

CatalogEntries represent discovered data objects in the unified enterprise
catalog. Uses a hierarchical model with parent_id supporting entry types:
DATABASE, SCHEMA, TABLE, VIEW, COLLECTION, DATASET, DOCUMENT, SHEET.

Enriched with semantic metadata for cross-source intelligence and
natural language querying.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class CatalogEntry(AppBase):
    """Enterprise data catalog entry with hierarchical and semantic metadata."""

    __tablename__ = "catalog_entries"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    data_source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=False
    )
    # Self-referencing FK for hierarchical catalog (DATABASE → SCHEMA → TABLE)
    parent_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_entries.id"), nullable=True
    )
    catalog_version_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_versions.id"), nullable=False
    )

    # Entry classification
    entry_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )
    technical_name: Mapped[str] = mapped_column(
        sa.String(255), nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    schema_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    database_name: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    domain: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    description: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )

    # Semantic metadata
    semantic_metadata: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default=sa.text("'{}'::jsonb"),
    )
    confidence_score: Mapped[float | None] = mapped_column(
        sa.Numeric(5, 4), nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="active"
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
    parent: Mapped["CatalogEntry | None"] = relationship(
        "CatalogEntry",
        remote_side=[id],
        back_populates="children",
        lazy="selectin",
    )
    children: Mapped[list["CatalogEntry"]] = relationship(
        "CatalogEntry",
        back_populates="parent",
        lazy="selectin",
    )
    catalog_version: Mapped["CatalogVersion"] = relationship(
        "CatalogVersion", lazy="selectin"
    )
    catalog_fields: Mapped[list["CatalogField"]] = relationship(
        "CatalogField", back_populates="catalog_entry", lazy="selectin"
    )
    project_mappings: Mapped[list["CatalogProjectMapping"]] = relationship(
        "CatalogProjectMapping", back_populates="catalog_entry", lazy="selectin"
    )
    project_source_mappings: Mapped[list["ProjectSourceMapping"]] = relationship(
        "ProjectSourceMapping", back_populates="catalog_entry", lazy="selectin"
    )
    outgoing_relationships: Mapped[list["CatalogRelationship"]] = relationship(
        "CatalogRelationship",
        foreign_keys="[CatalogRelationship.source_entry_id]",
        back_populates="source_entry",
        lazy="selectin",
    )
    incoming_relationships: Mapped[list["CatalogRelationship"]] = relationship(
        "CatalogRelationship",
        foreign_keys="[CatalogRelationship.target_entry_id]",
        back_populates="target_entry",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<CatalogEntry id={self.id} technical_name={self.technical_name} "
            f"type={self.entry_type}>"
        )
