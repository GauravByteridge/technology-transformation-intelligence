"""
DataSource and SourceConnection ORM models for App_DB.

DataSources represent external data connections (PostgreSQL, MongoDB, etc.).
SourceConnections link data sources to projects, enabling multi-source
project contexts for AI queries.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class DataSource(AppBase):
    """External data source configuration (PostgreSQL, MongoDB, etc.)."""

    __tablename__ = "data_sources"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    display_label: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    connection_config: Mapped[dict] = mapped_column(
        sa.JSON, nullable=False, default=dict
    )
    connection_status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="disconnected"
    )
    last_connected_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
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
    source_connections: Mapped[list["SourceConnection"]] = relationship(
        "SourceConnection", back_populates="data_source", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<DataSource id={self.id} name={self.name} type={self.source_type}>"


class SourceConnection(AppBase):
    """Links a data source to a project with a stated purpose."""

    __tablename__ = "source_connections"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    data_source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(sa.String(255), nullable=False)
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
    project: Mapped["Project"] = relationship(
        "Project", back_populates="source_connections"
    )
    data_source: Mapped["DataSource"] = relationship(
        "DataSource", back_populates="source_connections"
    )

    # Unique constraint: a data source can only be connected once per project
    __table_args__ = (
        sa.UniqueConstraint(
            "project_id", "data_source_id",
            name="uq_source_connections_project_data_source",
        ),
    )

    def __repr__(self) -> str:
        return f"<SourceConnection project_id={self.project_id} data_source_id={self.data_source_id}>"
