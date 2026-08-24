"""Phase 8 project_source_mappings table — links projects to catalog entries.

Revision ID: 005_phase8_project_source_mappings
Revises: 004_phase8_catalog_entries
Create Date: 2025-01-25 00:00:00.000000

Creates table:
- project_source_mappings (project ↔ catalog entry mapping with project_field)

The catalog belongs to data sources, not projects. This table provides the
relationship layer that maps specific catalog entries to projects via the
field used for project filtering.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers used by Alembic.
revision = "005_project_src_mappings"
down_revision = "004_catalog_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create project_source_mappings table with indexes and constraints."""

    op.create_table(
        "project_source_mappings",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("catalog_entry_id", sa.UUID(), nullable=False),
        sa.Column("project_field", sa.String(255), nullable=False),
        sa.Column(
            "mapping_type",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'discovered'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_source_mappings"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_project_source_mappings_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name="fk_project_source_mappings_source_id_data_sources",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_entry_id"],
            ["catalog_entries.id"],
            name="fk_project_source_mappings_catalog_entry_id_catalog_entries",
        ),
        sa.UniqueConstraint(
            "project_id",
            "catalog_entry_id",
            name="uq_project_source_mappings_project_catalog_entry",
        ),
    )

    op.create_index(
        "ix_project_source_mappings_project_id",
        "project_source_mappings",
        ["project_id"],
    )
    op.create_index(
        "ix_project_source_mappings_source_id",
        "project_source_mappings",
        ["source_id"],
    )


def downgrade() -> None:
    """Drop project_source_mappings table and its indexes."""

    op.drop_index(
        "ix_project_source_mappings_source_id",
        table_name="project_source_mappings",
    )
    op.drop_index(
        "ix_project_source_mappings_project_id",
        table_name="project_source_mappings",
    )
    op.drop_table("project_source_mappings")
