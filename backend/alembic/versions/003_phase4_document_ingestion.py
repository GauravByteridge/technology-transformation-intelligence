"""Phase 4 document ingestion schema — datasets, regions, columns, records, relationships.

Revision ID: 003_phase4_document_ingestion
Revises: 002_business_data_models
Create Date: 2025-01-20 00:00:00.000000

Changes:
- ALTER uploaded_files.project_id DROP NOT NULL
- CREATE TABLE datasets
- CREATE TABLE data_regions
- CREATE TABLE dataset_columns
- CREATE TABLE dataset_records (with GIN index on JSONB data column)
- CREATE TABLE dataset_relationships

All tables use UUID primary keys with gen_random_uuid() defaults and include
created_at timestamps. Datasets and dataset_columns also include updated_at.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers used by Alembic.
revision = "003_phase4_document_ingestion"
down_revision = "002_business_data_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Phase 4 document ingestion tables and alter uploaded_files."""

    # --- ALTER uploaded_files.project_id to allow NULL ---
    op.alter_column(
        "uploaded_files",
        "project_id",
        existing_type=sa.UUID(),
        nullable=True,
    )

    # --- datasets ---
    op.create_table(
        "datasets",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(100), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("sheet_name", sa.String(255), nullable=True),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column(
            "record_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'REVIEW_REQUIRED'"),
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_datasets"),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["uploaded_files.id"],
            name="fk_datasets_file_id_uploaded_files",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_datasets_project_id_projects",
        ),
    )
    op.create_index("ix_datasets_file_id", "datasets", ["file_id"])
    op.create_index("ix_datasets_project_id", "datasets", ["project_id"])

    # --- data_regions ---
    op.create_table(
        "data_regions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=True),
        sa.Column("sheet_name", sa.String(255), nullable=False),
        sa.Column("start_row", sa.Integer(), nullable=False),
        sa.Column("end_row", sa.Integer(), nullable=False),
        sa.Column("start_column", sa.Integer(), nullable=False),
        sa.Column("end_column", sa.Integer(), nullable=False),
        sa.Column("header_row", sa.Integer(), nullable=True),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column("processing_strategy", sa.String(20), nullable=False),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column("classification_reason", sa.Text(), nullable=True),
        sa.Column("warnings", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_data_regions"),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["uploaded_files.id"],
            name="fk_data_regions_file_id_uploaded_files",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name="fk_data_regions_dataset_id_datasets",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_data_regions_file_id", "data_regions", ["file_id"])
    op.create_index("ix_data_regions_dataset_id", "data_regions", ["dataset_id"])

    # --- dataset_columns ---
    op.create_table(
        "dataset_columns",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("data_type", sa.String(20), nullable=False),
        sa.Column(
            "nullable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("column_index", sa.Integer(), nullable=False),
        sa.Column("sample_values", sa.Text(), nullable=True),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_columns"),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name="fk_dataset_columns_dataset_id_datasets",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_dataset_columns_dataset_id", "dataset_columns", ["dataset_id"]
    )

    # --- dataset_records ---
    op.create_table(
        "dataset_records",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_sheet", sa.String(255), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_records"),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name="fk_dataset_records_dataset_id_datasets",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_dataset_records_dataset_id", "dataset_records", ["dataset_id"]
    )
    op.create_index(
        "ix_dataset_records_data",
        "dataset_records",
        ["data"],
        postgresql_using="gin",
    )

    # --- dataset_relationships ---
    op.create_table(
        "dataset_relationships",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_dataset_id", sa.UUID(), nullable=False),
        sa.Column("target_dataset_id", sa.UUID(), nullable=False),
        sa.Column("source_column", sa.String(255), nullable=False),
        sa.Column("target_column", sa.String(255), nullable=False),
        sa.Column("relationship_type", sa.String(30), nullable=False),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_relationships"),
        sa.ForeignKeyConstraint(
            ["source_dataset_id"],
            ["datasets.id"],
            name="fk_dataset_relationships_source_dataset_id_datasets",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_dataset_id"],
            ["datasets.id"],
            name="fk_dataset_relationships_target_dataset_id_datasets",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    """Drop Phase 4 tables and restore uploaded_files.project_id NOT NULL."""

    op.drop_table("dataset_relationships")
    op.drop_index("ix_dataset_records_data", table_name="dataset_records")
    op.drop_index("ix_dataset_records_dataset_id", table_name="dataset_records")
    op.drop_table("dataset_records")
    op.drop_index("ix_dataset_columns_dataset_id", table_name="dataset_columns")
    op.drop_table("dataset_columns")
    op.drop_index("ix_data_regions_dataset_id", table_name="data_regions")
    op.drop_index("ix_data_regions_file_id", table_name="data_regions")
    op.drop_table("data_regions")
    op.drop_index("ix_datasets_project_id", table_name="datasets")
    op.drop_index("ix_datasets_file_id", table_name="datasets")
    op.drop_table("datasets")

    # Restore NOT NULL on uploaded_files.project_id
    op.alter_column(
        "uploaded_files",
        "project_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
