"""Phase 8 catalog entries — enterprise data catalog for cross-source intelligence.

Revision ID: 004_phase8_catalog_entries
Revises: 003_phase4_document_ingestion
Create Date: 2025-01-25 00:00:00.000000

Creates tables:
- catalog_entries (technical + semantic metadata for discovered data objects)

Adds indexes:
- GIN index on domain_tags for tag-based filtering
- GIN index on query_capabilities for capability search
- Standard index on source_id for FK lookups
- UNIQUE constraint on (source_id, object_name, version)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers used by Alembic.
revision = "004_catalog_entries"
down_revision = "003_phase4_document_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create catalog_entries table with semantic metadata support."""

    op.create_table(
        "catalog_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        # Technical metadata
        sa.Column("database_name", sa.String(255), nullable=True),
        sa.Column("schema_name", sa.String(255), nullable=True),
        sa.Column("object_name", sa.String(255), nullable=False),
        sa.Column("object_type", sa.String(50), nullable=False),
        sa.Column(
            "fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "primary_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "foreign_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "indexes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # Semantic metadata
        sa.Column("semantic_name", sa.String(500), nullable=True),
        sa.Column("semantic_description", sa.Text(), nullable=True),
        sa.Column(
            "domain_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "query_capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "suggested_queries",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "confidence",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'medium'"),
        ),
        sa.Column(
            "project_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # Versioning
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_catalog_entries"),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name="fk_catalog_entries_source_id_data_sources",
        ),
        sa.UniqueConstraint(
            "source_id",
            "object_name",
            "version",
            name="uq_catalog_entries_source_object_version",
        ),
    )

    # Standard index on source_id for FK lookups
    op.create_index(
        "ix_catalog_entries_source_id",
        "catalog_entries",
        ["source_id"],
    )

    # GIN index on domain_tags for tag-based filtering
    op.create_index(
        "ix_catalog_entries_domain_tags",
        "catalog_entries",
        ["domain_tags"],
        postgresql_using="gin",
    )

    # GIN index on query_capabilities for capability search
    op.create_index(
        "ix_catalog_entries_query_capabilities",
        "catalog_entries",
        ["query_capabilities"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Drop catalog_entries table and its indexes."""
    op.drop_index("ix_catalog_entries_query_capabilities", table_name="catalog_entries")
    op.drop_index("ix_catalog_entries_domain_tags", table_name="catalog_entries")
    op.drop_index("ix_catalog_entries_source_id", table_name="catalog_entries")
    op.drop_table("catalog_entries")
