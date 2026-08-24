"""
DataSourceCredential ORM model for App_DB.

Stores credential references for data sources without embedding
raw secrets in the database. Actual secrets are stored in a vault
or environment variables; this table holds only a reference pointer.
"""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class DataSourceCredential(AppBase):
    """Credential reference for a connected data source."""

    __tablename__ = "data_source_credentials"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    data_source_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("data_sources.id"), nullable=False
    )
    credential_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )
    # Reference to secret storage (e.g., "vault://...", "env://DB_PASS")
    secret_reference: Mapped[str] = mapped_column(
        sa.String(500), nullable=False
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
        "DataSource", back_populates="credentials"
    )

    def __repr__(self) -> str:
        return f"<DataSourceCredential id={self.id} type={self.credential_type}>"
