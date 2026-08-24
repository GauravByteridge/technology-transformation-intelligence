"""
CatalogRelationship ORM model for App_DB.

Represents discovered or declared relationships between catalog entries
(e.g., foreign key links across PostgreSQL tables, cross-source joins
via project_id between PostgreSQL and MongoDB collections).
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class CatalogRelationship(AppBase):
    """Relationship between two catalog entries for AI join intelligence."""

    __tablename__ = "catalog_relationships"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    source_entry_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_entries.id"), nullable=False
    )
    target_entry_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_entries.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )
    source_field_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_fields.id"), nullable=True
    )
    target_field_id: Mapped[UUID | None] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_fields.id"), nullable=True
    )
    confidence_score: Mapped[float | None] = mapped_column(
        sa.Numeric(5, 4), nullable=True
    )
    discovered_by: Mapped[str] = mapped_column(
        sa.String(100), nullable=False, default="discovery_engine"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    source_entry: Mapped["CatalogEntry"] = relationship(
        "CatalogEntry",
        foreign_keys=[source_entry_id],
        back_populates="outgoing_relationships",
    )
    target_entry: Mapped["CatalogEntry"] = relationship(
        "CatalogEntry",
        foreign_keys=[target_entry_id],
        back_populates="incoming_relationships",
    )

    def __repr__(self) -> str:
        return (
            f"<CatalogRelationship id={self.id} "
            f"type={self.relationship_type}>"
        )
