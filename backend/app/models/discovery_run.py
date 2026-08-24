"""
DataSourceDiscoveryRun ORM model for App_DB.

Records each discovery execution against a data source,
tracking status, duration, and objects found. Powers the
discovery history UI and catalog versioning.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class DataSourceDiscoveryRun(AppBase):
    """Record of a single discovery execution against a data source."""

    __tablename__ = "data_source_discovery_runs"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    data_source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="running"
    )
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    objects_discovered: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    fields_discovered: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )
    catalog_version: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    data_source: Mapped["DataSource"] = relationship(
        "DataSource", back_populates="discovery_runs"
    )

    def __repr__(self) -> str:
        return f"<DiscoveryRun id={self.id} status={self.status}>"
