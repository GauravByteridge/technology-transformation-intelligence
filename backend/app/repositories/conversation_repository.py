"""
Conversation repository — database access layer for conversation entities.

Phase 0: Interface stub with minimal method signatures.
Full implementation deferred to conversation feature phase.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """
    Encapsulates all database access for Conversation entities.

    Phase 0: Stub with interface definitions.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, Conversation)

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        """
        Retrieve a conversation by its primary key.

        Args:
            conversation_id: UUID of the conversation to retrieve.

        Returns:
            Conversation model instance, or None if not found.
        """
        return await self._get_by_id(conversation_id)

    async def list_by_project(self, project_id: UUID) -> list[Conversation]:
        """
        Retrieve all conversations for a given project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of Conversation instances for the project.
        """
        raise NotImplementedError(
            "ConversationRepository.list_by_project — deferred to conversation feature phase"
        )
