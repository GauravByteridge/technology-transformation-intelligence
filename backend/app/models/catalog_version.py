"""
CatalogVersion ORM model for App_DB.

Tracks versioned discovery snapshots for each data source.
When a new discovery completes, a new catalog version is created.
If discovery fails, the previous version remains current.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class CatalogVersion(AppBase):
    """Versioned catalog snapshot tied to a discovery run."""

    __tablename__ = "catalog_versions"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    data_source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="PENDING"
    )
    discovery_run_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_source_discovery_runs.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    data_source: Mapped["DataSource"] = relationship(
        "DataSource", back_populates="catalog_versions"
    )
    discovery_run: Mapped["DataSourceDiscoveryRun"] = relationship(
        "DataSourceDiscoveryRun"
    )

    # Unique constraint: one version number per data source
    __table_args__ = (
        sa.UniqueConstraint(
            "data_source_id", "version_number",
            name="uq_catalog_versions_source_version",
        ),
    )

    def __repr__(self) -> str:
        return f"<CatalogVersion id={self.id} v={self.version_number}>"
