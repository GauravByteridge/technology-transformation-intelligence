"""
CatalogProjectMapping ORM model for App_DB.

Links catalog entries to projects, enabling the AI to understand
which datasets are relevant to which project. Supports automatic
mapping (via project_key fields) and manual user assignments.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class CatalogProjectMapping(AppBase):
    """Maps a catalog entry to a project with mapping metadata."""

    __tablename__ = "catalog_project_mappings"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    catalog_entry_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_entries.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    mapping_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="automatic"
    )
    mapping_expression: Mapped[dict | None] = mapped_column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(
        sa.Numeric(5, 4), nullable=True
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
        "CatalogEntry", back_populates="project_mappings"
    )
    project: Mapped["Project"] = relationship("Project")

    # Unique constraint: one mapping per catalog entry + project
    __table_args__ = (
        sa.UniqueConstraint(
            "catalog_entry_id", "project_id",
            name="uq_catalog_project_mappings_entry_project",
        ),
    )

    def __repr__(self) -> str:
        return f"<CatalogProjectMapping entry={self.catalog_entry_id} project={self.project_id}>"
