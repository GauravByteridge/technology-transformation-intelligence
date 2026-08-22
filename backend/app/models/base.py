"""
SQLAlchemy DeclarativeBase for all ORM models in the platform.

All App_DB and RAG_DB models inherit from this base class. The separate
bases allow Alembic autogenerate to target the correct database by importing
the appropriate metadata.

NOTE: Two separate bases are used because App_DB and RAG_DB are distinct
logical databases with independent migration histories.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming conventions for consistent constraint names across migrations.
# This avoids Alembic generating random constraint names.
APP_DB_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

RAG_DB_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class AppBase(DeclarativeBase):
    """
    Base class for all App_DB models (users, projects, conversations, etc.).

    Provides:
    - Consistent naming conventions for database constraints
    - Common columns (id, created_at, updated_at) via mixins if desired
    """

    metadata = MetaData(naming_convention=APP_DB_NAMING_CONVENTION)


class RAGBase(DeclarativeBase):
    """
    Base class for all RAG_DB models (documents, chunks, embeddings).

    Separate from AppBase because RAG_DB is a distinct logical database
    with its own migration history and pgvector extension.
    """

    metadata = MetaData(naming_convention=RAG_DB_NAMING_CONVENTION)
