"""Create initial RAG_DB schema (documents, chunks, metadata, embeddings).

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:00:01.000000

Creates the core tables for the document intelligence pipeline:
- documents: Uploaded file tracking and processing state
- document_chunks: Text chunks with positional metadata
- document_metadata: Flexible key-value metadata per document
- embeddings: Vector embeddings for similarity search

The embedding vector dimension is fixed at 1536 (OpenAI ada-002 default).
Runtime validation against EMBEDDING_DIMENSION env var is handled by the
application settings layer, not by the migration.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# Revision identifiers used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Hard-coded dimension for this migration snapshot.
# The configurable EMBEDDING_DIMENSION env var is used at runtime for validation.
EMBEDDING_DIMENSION = 1536


def upgrade() -> None:
    """Create RAG_DB tables."""

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("processing_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- document_chunks ---
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- document_metadata ---
    op.create_table(
        "document_metadata",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.String(2048), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- embeddings ---
    op.create_table(
        "embeddings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "chunk_id",
            sa.Uuid(),
            sa.ForeignKey("document_chunks.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Drop RAG_DB tables in reverse dependency order."""
    op.drop_table("embeddings")
    op.drop_table("document_metadata")
    op.drop_table("document_chunks")
    op.drop_table("documents")
