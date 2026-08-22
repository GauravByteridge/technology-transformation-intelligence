"""Enable pgvector extension for vector similarity search.

Revision ID: 001
Revises: (none)
Create Date: 2025-01-01 00:00:00.000000

This migration enables the pgvector extension on RAG_DB, which provides
the `vector` data type and similarity search operators used by the
embeddings table.
"""

from typing import Sequence, Union

from alembic import op

# Revision identifiers used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable the pgvector extension."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Remove the pgvector extension."""
    op.execute("DROP EXTENSION IF EXISTS vector")
