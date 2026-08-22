"""
Conversation repository — database access layer for conversation and message entities.

Provides typed, parameterized access to the conversations and messages tables in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """
    Encapsulates all database access for Conversation and Message entities.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
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
        statement = select(Conversation).where(
            Conversation.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create_conversation(self, entity: Conversation) -> Conversation:
        """
        Persist a new conversation to the database.

        Args:
            entity: Conversation model instance to persist.

        Returns:
            The persisted Conversation with server-generated fields populated.
        """
        return await self._create(entity)

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        """
        Delete a conversation by its primary key.

        Args:
            conversation_id: UUID of the conversation to delete.

        Returns:
            True if the conversation was deleted, False if not found.
        """
        return await self._delete_by_id(conversation_id)

    async def add_message(self, message: Message) -> Message:
        """
        Persist a new message to the database.

        Args:
            message: Message model instance to persist.

        Returns:
            The persisted Message with server-generated fields populated.
        """
        self._session.add(message)
        await self._session.flush()
        await self._session.refresh(message)
        return message

    async def list_messages(self, conversation_id: UUID) -> list[Message]:
        """
        Retrieve all messages for a given conversation, ordered by creation time.

        Args:
            conversation_id: UUID of the conversation whose messages to retrieve.

        Returns:
            List of Message instances ordered by created_at ascending.
        """
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
