"""Add source_type column to documents table.

Revision ID: 004
Revises: 003
Create Date: 2026-08-27

Tracks the origin of each document:
- 'upload': manually uploaded file
- 'email': indexed from Gmail
- 'jira': from Jira attachment
- 'api': ingested via API
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source_type column with default 'upload'."""
    op.add_column(
        "documents",
        sa.Column("source_type", sa.String(50), nullable=False, server_default="upload"),
    )


def downgrade() -> None:
    """Remove source_type column."""
    op.drop_column("documents", "source_type")
