"""Initial App_DB schema — all application state tables.

Revision ID: 001_initial
Revises: (none)
Create Date: 2025-01-01 00:00:00.000000

Creates tables:
- users
- projects
- project_members
- data_sources
- source_connections
- conversations
- messages
- query_history
- saved_queries
- uploaded_files
- audit_logs

All tables use UUID primary keys and include created_at/updated_at timestamps.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all App_DB tables."""

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name="fk_projects_created_by_users",
        ),
    )

    # --- project_members ---
    op.create_table(
        "project_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_project_members"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_project_members_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_project_members_user_id_users",
        ),
        sa.UniqueConstraint(
            "project_id", "user_id",
            name="uq_project_members_project_user",
        ),
    )

    # --- data_sources ---
    op.create_table(
        "data_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("display_label", sa.String(255), nullable=False),
        sa.Column("connection_config", sa.JSON(), nullable=False),
        sa.Column("connection_status", sa.String(50), nullable=False),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_data_sources"),
    )

    # --- source_connections ---
    op.create_table(
        "source_connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("data_source_id", sa.UUID(), nullable=False),
        sa.Column("purpose", sa.String(255), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_source_connections"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_source_connections_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"], ["data_sources.id"],
            name="fk_source_connections_data_source_id_data_sources",
        ),
        sa.UniqueConstraint(
            "project_id", "data_source_id",
            name="uq_source_connections_project_data_source",
        ),
    )

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_conversations_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_conversations_user_id_users",
        ),
    )

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"],
            name="fk_messages_conversation_id_conversations",
        ),
    )

    # --- query_history ---
    op.create_table(
        "query_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("query_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("tools_invoked", sa.JSON(), nullable=True),
        sa.Column("sources_consulted", sa.JSON(), nullable=True),
        sa.Column("is_partial", sa.Boolean(), nullable=False),
        sa.Column("llm_provider", sa.String(100), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_query_history"),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"],
            name="fk_query_history_conversation_id_conversations",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_query_history_project_id_projects",
        ),
    )
    op.create_index("ix_query_history_query_id", "query_history", ["query_id"])

    # --- saved_queries ---
    op.create_table(
        "saved_queries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_saved_queries"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_saved_queries_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_saved_queries_project_id_projects",
        ),
    )

    # --- uploaded_files ---
    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("data_source_id", sa.UUID(), nullable=True),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("processing_status", sa.String(50), nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.UUID(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id", name="pk_uploaded_files"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_uploaded_files_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"], ["data_sources.id"],
            name="fk_uploaded_files_data_source_id_data_sources",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"], ["users.id"],
            name="fk_uploaded_files_uploaded_by_users",
        ),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_audit_logs_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_audit_logs_project_id_projects",
        ),
    )


def downgrade() -> None:
    """Drop all App_DB tables in reverse dependency order."""
    op.drop_table("audit_logs")
    op.drop_table("uploaded_files")
    op.drop_table("saved_queries")
    op.drop_index("ix_query_history_query_id", table_name="query_history")
    op.drop_table("query_history")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("source_connections")
    op.drop_table("data_sources")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("users")
