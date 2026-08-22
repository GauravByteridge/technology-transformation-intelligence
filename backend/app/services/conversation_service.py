"""
Conversation service — business logic layer for conversation and message operations.

Manages conversation CRUD with project existence verification
and message management within conversations.
"""

import structlog
from uuid import UUID

from app.constants import SYSTEM_USER_ID
from app.errors.conversation_errors import ConversationNotFoundError
from app.errors.project_errors import ProjectNotFoundError
from app.models.conversation import Conversation, Message
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.project_repository import ProjectRepository

logger = structlog.get_logger(__name__)


class ConversationService:
    """
    Business logic for conversation and message operations.

    Enforces project existence before creating conversations and
    conversation existence before adding messages.
    """

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        project_repository: ProjectRepository,
    ) -> None:
        """
        Initialize with required dependencies.

        Args:
            conversation_repository: Repository for conversation persistence.
            project_repository: Repository for project existence checks.
        """
        self._conversation_repo = conversation_repository
        self._project_repo = project_repository

    async def create_conversation(
        self,
        project_id: UUID,
        title: str | None = None,
    ) -> dict:
        """
        Create a new conversation scoped to a project.

        Verifies project exists and assigns SYSTEM_USER_ID as the owner.

        Args:
            project_id: UUID of the project this conversation belongs to.
            title: Optional title for the conversation.

        Returns:
            Dictionary with conversation fields.

        Raises:
            ProjectNotFoundError: If the project does not exist.
        """
        project = await self._project_repo.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id=str(project_id))

        conversation = Conversation(
            project_id=project_id,
            user_id=SYSTEM_USER_ID,
            title=title,
        )

        created = await self._conversation_repo.create_conversation(conversation)

        logger.info(
            "conversation_created",
            conversation_id=str(created.id),
            project_id=str(project_id),
        )

        return self._to_response(created)

    async def get_conversation(self, conversation_id: UUID) -> dict:
        """
        Retrieve a conversation by ID, including its messages.

        Args:
            conversation_id: UUID of the conversation.

        Returns:
            Dictionary with conversation fields and messages list.

        Raises:
            ConversationNotFoundError: If the conversation does not exist.
        """
        conversation = await self._conversation_repo.get_conversation(conversation_id)

        if conversation is None:
            logger.info(
                "conversation_not_found",
                conversation_id=str(conversation_id),
            )
            raise ConversationNotFoundError(conversation_id=str(conversation_id))

        messages = await self._conversation_repo.list_messages(conversation_id)

        response = self._to_response(conversation)
        response["messages"] = [self._message_to_response(m) for m in messages]

        return response

    async def list_by_project(self, project_id: UUID) -> list[dict]:
        """
        List all conversations for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of conversation dictionaries.
        """
        conversations = await self._conversation_repo.list_by_project(project_id)

        logger.debug(
            "conversations_listed",
            project_id=str(project_id),
            total=len(conversations),
        )

        return [self._to_response(c) for c in conversations]

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> dict:
        """
        Add a message to an existing conversation.

        Args:
            conversation_id: UUID of the conversation.
            role: Message role (e.g., "user", "assistant").
            content: Message text content.
            metadata: Optional metadata for the message.

        Returns:
            Dictionary with message fields.

        Raises:
            ConversationNotFoundError: If the conversation does not exist.
        """
        conversation = await self._conversation_repo.get_conversation(conversation_id)

        if conversation is None:
            raise ConversationNotFoundError(conversation_id=str(conversation_id))

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_=metadata,
        )

        created = await self._conversation_repo.add_message(message)

        logger.info(
            "message_added",
            conversation_id=str(conversation_id),
            message_id=str(created.id),
            role=role,
        )

        return self._message_to_response(created)

    async def delete_conversation(self, conversation_id: UUID) -> None:
        """
        Delete a conversation by ID.

        Args:
            conversation_id: UUID of the conversation to delete.

        Raises:
            ConversationNotFoundError: If the conversation does not exist.
        """
        deleted = await self._conversation_repo.delete_conversation(conversation_id)

        if not deleted:
            logger.info(
                "conversation_not_found_for_delete",
                conversation_id=str(conversation_id),
            )
            raise ConversationNotFoundError(conversation_id=str(conversation_id))

        logger.info(
            "conversation_deleted",
            conversation_id=str(conversation_id),
        )

    # --- Private Helpers ---

    def _to_response(self, conversation: Conversation) -> dict:
        """Convert a Conversation model to a response dict."""
        return {
            "id": conversation.id,
            "project_id": conversation.project_id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }

    def _message_to_response(self, message: Message) -> dict:
        """Convert a Message model to a response dict."""
        return {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "role": message.role,
            "content": message.content,
            "metadata": message.metadata_,
            "created_at": message.created_at,
        }
