"""
ProjectSourceMapping ORM model for App_DB.

Maps specific catalog entries to projects, linking through the data source.
This provides the relationship layer between projects and their relevant
catalog entries, with the project_field indicating which field in the
catalog entry's schema identifies the project.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class ProjectSourceMapping(AppBase):
    """Links a project to a catalog entry via its data source."""

    __tablename__ = "project_source_mappings"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=False
    )
    catalog_entry_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("catalog_entries.id"), nullable=False
    )
    project_field: Mapped[str] = mapped_column(
        sa.String(255), nullable=False
    )
    mapping_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, server_default=sa.text("'discovered'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="source_mappings"
    )
    data_source: Mapped["DataSource"] = relationship(
        "DataSource", back_populates="project_source_mappings"
    )
    catalog_entry: Mapped["CatalogEntry"] = relationship(
        "CatalogEntry", back_populates="project_source_mappings"
    )

    # Unique constraint: a catalog entry can only be mapped once per project
    __table_args__ = (
        sa.UniqueConstraint(
            "project_id",
            "catalog_entry_id",
            name="uq_project_source_mappings_project_catalog_entry",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectSourceMapping project_id={self.project_id} "
            f"catalog_entry_id={self.catalog_entry_id}>"
        )
