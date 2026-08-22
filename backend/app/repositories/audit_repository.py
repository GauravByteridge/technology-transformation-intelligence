"""
AuditLog repository — database access layer for audit log entities.

Phase 0: Interface stub with minimal method signatures.
Full implementation deferred to audit feature phase.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """
    Encapsulates all database access for AuditLog entities.

    Phase 0: Stub with interface definitions.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, AuditLog)

    async def get_audit_log(self, audit_log_id: UUID) -> AuditLog | None:
        """
        Retrieve an audit log entry by its primary key.

        Args:
            audit_log_id: UUID of the audit log record.

        Returns:
            AuditLog model instance, or None if not found.
        """
        return await self._get_by_id(audit_log_id)

    async def list_by_project(self, project_id: UUID) -> list[AuditLog]:
        """
        Retrieve all audit log entries for a given project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of AuditLog instances for the project.
        """
        raise NotImplementedError(
            "AuditLogRepository.list_by_project — deferred to audit feature phase"
        )
