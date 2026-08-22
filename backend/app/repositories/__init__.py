"""
Repository layer — database access for internal databases (App_DB, RAG_DB).

All repositories inherit from BaseRepository which enforces parameterized queries.
See base.py for security invariants and usage patterns.
"""

from app.repositories.audit_repository import AuditLogRepository
from app.repositories.base import BaseRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.query_history_repository import QueryHistoryRepository
from app.repositories.source_connection_repository import SourceConnectionRepository

__all__ = [
    "AuditLogRepository",
    "BaseRepository",
    "ConversationRepository",
    "DataSourceRepository",
    "FileRepository",
    "ProjectRepository",
    "QueryHistoryRepository",
    "SourceConnectionRepository",
]
