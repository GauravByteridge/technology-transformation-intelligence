"""
ORM models for the Technology Transformation Intelligence platform.

Models are organized by database:
- AppBase subclasses → App_DB (application state)
- RAGBase subclasses → RAG_DB (documents, embeddings)

Import all models here so Alembic autogenerate can detect them.
"""

from app.models.base import AppBase, RAGBase

# App_DB models
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.data_source import DataSource, SourceConnection
from app.models.conversation import Conversation, Message
from app.models.query import QueryHistory, SavedQuery
from app.models.uploaded_file import UploadedFile
from app.models.audit import AuditLog

# RAG_DB models
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentMetadata,
    Embedding,
    EMBEDDING_DIMENSION,
)

__all__ = [
    "AppBase",
    "RAGBase",
    # App_DB models
    "User",
    "Project",
    "ProjectMember",
    "DataSource",
    "SourceConnection",
    "Conversation",
    "Message",
    "QueryHistory",
    "SavedQuery",
    "UploadedFile",
    "AuditLog",
    # RAG_DB models
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    "Embedding",
    "EMBEDDING_DIMENSION",
]
