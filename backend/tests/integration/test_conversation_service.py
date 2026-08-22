"""
Integration tests for ConversationService against SQLite.

Verifies: CRUD operations, SYSTEM_USER_ID assignment, project existence checks,
message handling, conversation not-found errors.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.conversation_errors import ConversationNotFoundError
from app.errors.project_errors import ProjectNotFoundError
from app.models.project import Project
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.project_repository import ProjectRepository
from app.services.conversation_service import ConversationService

# Use a proper uuid4 to avoid Python 3.14 SQLite UUID storage edge case
TEST_SYSTEM_USER_ID = uuid4()


async def _setup(session: AsyncSession):
    """Create system user and project for conversation tests."""
    user = User(id=TEST_SYSTEM_USER_ID, email="system@test.com", name="System", role="system")
    session.add(user)
    await session.flush()

    project = Project(name="Conv Project", created_by=TEST_SYSTEM_USER_ID)
    session.add(project)
    await session.flush()
    await session.refresh(project)

    service = ConversationService(
        conversation_repository=ConversationRepository(session),
        project_repository=ProjectRepository(session),
    )

    return service, project.id


class TestConversationService:
    """Integration tests for ConversationService."""

    @pytest.mark.asyncio
    async def test_create_conversation_assigns_system_user_id(self, async_session: AsyncSession):
        service, project_id = await _setup(async_session)

        with patch("app.services.conversation_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            result = await service.create_conversation(project_id=project_id, title="Test Chat")

        assert result["project_id"] == project_id
        assert result["user_id"] == TEST_SYSTEM_USER_ID
        assert result["title"] == "Test Chat"

    @pytest.mark.asyncio
    async def test_create_conversation_raises_when_project_missing(self, async_session: AsyncSession):
        service, _ = await _setup(async_session)

        with patch("app.services.conversation_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            with pytest.raises(ProjectNotFoundError):
                await service.create_conversation(project_id=uuid4(), title="No Project")

    @pytest.mark.asyncio
    async def test_get_conversation_includes_messages(self, async_session: AsyncSession):
        service, project_id = await _setup(async_session)

        with patch("app.services.conversation_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            conv = await service.create_conversation(project_id=project_id, title="With Messages")
            await service.add_message(conv["id"], role="user", content="Hello")
            await service.add_message(conv["id"], role="assistant", content="Hi there")

            result = await service.get_conversation(conv["id"])

        assert result["id"] == conv["id"]
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_conversation_raises_when_not_found(self, async_session: AsyncSession):
        service, _ = await _setup(async_session)

        with pytest.raises(ConversationNotFoundError):
            await service.get_conversation(uuid4())

    @pytest.mark.asyncio
    async def test_list_by_project_returns_conversations(self, async_session: AsyncSession):
        service, project_id = await _setup(async_session)

        with patch("app.services.conversation_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            await service.create_conversation(project_id=project_id, title="Chat 1")
            await service.create_conversation(project_id=project_id, title="Chat 2")

            results = await service.list_by_project(project_id)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_add_message_raises_when_conversation_missing(self, async_session: AsyncSession):
        service, _ = await _setup(async_session)

        with pytest.raises(ConversationNotFoundError):
            await service.add_message(uuid4(), role="user", content="Hello?")

    @pytest.mark.asyncio
    async def test_delete_conversation_removes_it(self, async_session: AsyncSession):
        service, project_id = await _setup(async_session)

        with patch("app.services.conversation_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            conv = await service.create_conversation(project_id=project_id)
            await service.delete_conversation(conv["id"])

            with pytest.raises(ConversationNotFoundError):
                await service.get_conversation(conv["id"])

    @pytest.mark.asyncio
    async def test_delete_conversation_raises_when_not_found(self, async_session: AsyncSession):
        service, _ = await _setup(async_session)

        with pytest.raises(ConversationNotFoundError):
            await service.delete_conversation(uuid4())
