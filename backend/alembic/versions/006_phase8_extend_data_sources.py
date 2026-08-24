"""Phase 8 extend data_sources — add discovery tracking columns.

Revision ID: 006_phase8_extend_data_sources
Revises: 005_phase8_project_source_mappings
Create Date: 2025-01-25 00:00:00.000000

Adds columns to data_sources:
- last_discovery_at (TIMESTAMPTZ, nullable)
- discovery_status (VARCHAR(50), DEFAULT 'pending')
- objects_discovered (INTEGER, DEFAULT 0)
- fields_discovered (INTEGER, DEFAULT 0)
- discovery_error (TEXT, nullable)
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers used by Alembic.
revision = "006_extend_data_sources"
down_revision = "005_project_src_mappings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add discovery tracking columns to data_sources table."""

    op.add_column(
        "data_sources",
        sa.Column("last_discovery_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "data_sources",
        sa.Column(
            "discovery_status",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    op.add_column(
        "data_sources",
        sa.Column(
            "objects_discovered",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "data_sources",
        sa.Column(
            "fields_discovered",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "data_sources",
        sa.Column("discovery_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove discovery tracking columns from data_sources table."""

    op.drop_column("data_sources", "discovery_error")
    op.drop_column("data_sources", "fields_discovered")
    op.drop_column("data_sources", "objects_discovered")
    op.drop_column("data_sources", "discovery_status")
    op.drop_column("data_sources", "last_discovery_at")
