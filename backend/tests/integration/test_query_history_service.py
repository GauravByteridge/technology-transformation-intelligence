"""
Integration tests for QueryHistoryService against SQLite.

Verifies: create, list (descending order), saved query CRUD,
append-only enforcement (no update/delete on query_history), SYSTEM_USER_ID assignment.
"""

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.project_errors import ProjectNotFoundError
from app.errors.query_errors import QueryHistoryNotFoundError, SavedQueryNotFoundError
from app.models.conversation import Conversation
from app.models.project import Project
from app.models.query import QueryHistory
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.query_history_repository import QueryHistoryRepository
from app.services.query_history_service import QueryHistoryService

# Use a proper uuid4 to avoid Python 3.14 SQLite UUID storage edge case
TEST_SYSTEM_USER_ID = uuid4()


async def _setup(session: AsyncSession):
    """Create system user, project, and conversation for query history tests."""
    user = User(id=TEST_SYSTEM_USER_ID, email="system@test.com", name="System", role="system")
    session.add(user)
    await session.flush()

    project = Project(name="QH Project", created_by=TEST_SYSTEM_USER_ID)
    session.add(project)
    await session.flush()
    await session.refresh(project)

    conv = Conversation(project_id=project.id, user_id=TEST_SYSTEM_USER_ID)
    session.add(conv)
    await session.flush()
    await session.refresh(conv)

    service = QueryHistoryService(
        query_history_repository=QueryHistoryRepository(session),
        project_repository=ProjectRepository(session),
    )

    return service, project.id, conv.id


class TestQueryHistoryService:
    """Integration tests for QueryHistoryService."""

    @pytest.mark.asyncio
    async def test_create_query_history_verifies_project(self, async_session: AsyncSession):
        service, project_id, conv_id = await _setup(async_session)

        result = await service.create_query_history(
            project_id=project_id,
            conversation_id=conv_id,
            query_id=uuid4(),
            question="What is revenue?",
        )

        assert result["project_id"] == project_id
        assert result["question"] == "What is revenue?"

    @pytest.mark.asyncio
    async def test_create_query_history_raises_when_project_missing(self, async_session: AsyncSession):
        service, _, conv_id = await _setup(async_session)

        with pytest.raises(ProjectNotFoundError):
            await service.create_query_history(
                project_id=uuid4(),
                conversation_id=conv_id,
                query_id=uuid4(),
                question="No project",
            )

    @pytest.mark.asyncio
    async def test_get_query_history_returns_record(self, async_session: AsyncSession):
        service, project_id, conv_id = await _setup(async_session)
        created = await service.create_query_history(
            project_id=project_id,
            conversation_id=conv_id,
            query_id=uuid4(),
            question="Test Q",
        )

        result = await service.get_query_history(created["id"])

        assert result["id"] == created["id"]
        assert result["question"] == "Test Q"

    @pytest.mark.asyncio
    async def test_get_query_history_raises_when_not_found(self, async_session: AsyncSession):
        service, _, _ = await _setup(async_session)

        with pytest.raises(QueryHistoryNotFoundError):
            await service.get_query_history(uuid4())

    @pytest.mark.asyncio
    async def test_list_by_project_orders_descending(self, async_session: AsyncSession):
        service, project_id, conv_id = await _setup(async_session)

        repo = QueryHistoryRepository(async_session)
        earlier = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        later = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

        await repo.create_query_history(
            QueryHistory(
                query_id=uuid4(), conversation_id=conv_id,
                project_id=project_id, question="First", created_at=earlier,
            )
        )
        await repo.create_query_history(
            QueryHistory(
                query_id=uuid4(), conversation_id=conv_id,
                project_id=project_id, question="Second", created_at=later,
            )
        )

        results = await service.list_by_project(project_id)

        assert len(results) == 2
        assert results[0]["question"] == "Second"  # Newest first
        assert results[1]["question"] == "First"

    @pytest.mark.asyncio
    async def test_query_history_is_append_only(self, async_session: AsyncSession):
        """Verify no update or delete methods exist on the service for query history."""
        service, _, _ = await _setup(async_session)

        assert not hasattr(service, "update_query_history")
        assert not hasattr(service, "delete_query_history")


class TestSavedQueryService:
    """Integration tests for saved query operations in QueryHistoryService."""

    @pytest.mark.asyncio
    async def test_create_saved_query_assigns_system_user_id(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with patch("app.services.query_history_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            result = await service.create_saved_query(
                project_id=project_id,
                title="Revenue Query",
                question="What is total revenue?",
            )

        assert result["user_id"] == TEST_SYSTEM_USER_ID
        assert result["title"] == "Revenue Query"
        assert result["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_create_saved_query_raises_when_project_missing(self, async_session: AsyncSession):
        service, _, _ = await _setup(async_session)

        with patch("app.services.query_history_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            with pytest.raises(ProjectNotFoundError):
                await service.create_saved_query(
                    project_id=uuid4(),
                    title="No Project",
                    question="Q?",
                )

    @pytest.mark.asyncio
    async def test_list_saved_by_project(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with patch("app.services.query_history_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            await service.create_saved_query(project_id=project_id, title="Q1", question="Q1?")
            await service.create_saved_query(project_id=project_id, title="Q2", question="Q2?")

            results = await service.list_saved_by_project(project_id)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_delete_saved_query_removes_it(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with patch("app.services.query_history_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            saved = await service.create_saved_query(
                project_id=project_id, title="Delete Me", question="Q?"
            )

            await service.delete_saved_query(saved["id"])

            results = await service.list_saved_by_project(project_id)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_saved_query_raises_when_not_found(self, async_session: AsyncSession):
        service, _, _ = await _setup(async_session)

        with pytest.raises(SavedQueryNotFoundError):
            await service.delete_saved_query(uuid4())
