"""
Integration tests for repository layer against SQLite.

Tests cover:
- ProjectRepository: update_project, delete_project
- DataSourceRepository: full CRUD
- ConversationRepository: full CRUD including messages
- QueryHistoryRepository: append-only enforcement, saved queries
- FileRepository: full CRUD
- SourceConnectionRepository: create (duplicate → DuplicateSourceConnectionError), delete
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.datasource_errors import DuplicateSourceConnectionError
from app.models.conversation import Conversation, Message
from app.models.data_source import DataSource, SourceConnection
from app.models.project import Project
from app.models.query import QueryHistory, SavedQuery
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.query_history_repository import QueryHistoryRepository
from app.repositories.source_connection_repository import SourceConnectionRepository


# --- Helpers ---


async def create_test_user(session: AsyncSession) -> User:
    """Create a minimal user to satisfy FK constraints."""
    user = User(id=uuid4(), email=f"test-{uuid4()}@example.com", name="Test User", role="admin")
    session.add(user)
    await session.flush()
    return user


async def create_test_project(session: AsyncSession, user: User) -> Project:
    """Create a minimal project to satisfy FK constraints."""
    project = Project(id=uuid4(), name="Test Project", created_by=user.id)
    session.add(project)
    await session.flush()
    return project


async def create_test_data_source(session: AsyncSession) -> DataSource:
    """Create a minimal data source."""
    ds = DataSource(
        id=uuid4(),
        name="Test DS",
        source_type="postgresql",
        display_label="Test PostgreSQL",
        connection_config={"host": "localhost", "port": 5432},
    )
    session.add(ds)
    await session.flush()
    return ds


# --- ProjectRepository Tests ---


class TestProjectRepository:
    """Tests for ProjectRepository update and delete operations."""

    @pytest.mark.asyncio
    async def test_update_project_applies_partial_updates(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        repo = ProjectRepository(async_session)
        project = await repo.create_project(
            Project(id=uuid4(), name="Original", description="Desc", created_by=user.id)
        )

        updated = await repo.update_project(project.id, {"name": "Updated Name"})

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Desc"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_project_returns_none_when_not_found(self, async_session: AsyncSession):
        repo = ProjectRepository(async_session)

        result = await repo.update_project(uuid4(), {"name": "Nope"})

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_project_returns_true_when_exists(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        repo = ProjectRepository(async_session)
        project = await repo.create_project(
            Project(id=uuid4(), name="To Delete", created_by=user.id)
        )

        deleted = await repo.delete_project(project.id)

        assert deleted is True
        assert await repo.get_project(project.id) is None

    @pytest.mark.asyncio
    async def test_delete_project_returns_false_when_not_found(self, async_session: AsyncSession):
        repo = ProjectRepository(async_session)

        deleted = await repo.delete_project(uuid4())

        assert deleted is False


# --- DataSourceRepository Tests ---


class TestDataSourceRepository:
    """Tests for DataSourceRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_data_source(self, async_session: AsyncSession):
        repo = DataSourceRepository(async_session)
        ds = DataSource(
            id=uuid4(),
            name="My Source",
            source_type="mongodb",
            display_label="Mongo DB",
            connection_config={"uri": "mongodb://localhost:27017"},
        )

        created = await repo.create_data_source(ds)
        fetched = await repo.get_data_source(created.id)

        assert fetched is not None
        assert fetched.name == "My Source"
        assert fetched.source_type == "mongodb"

    @pytest.mark.asyncio
    async def test_list_data_sources_returns_all(self, async_session: AsyncSession):
        repo = DataSourceRepository(async_session)
        await repo.create_data_source(
            DataSource(id=uuid4(), name="DS1", source_type="pg", display_label="PG", connection_config={})
        )
        await repo.create_data_source(
            DataSource(id=uuid4(), name="DS2", source_type="mongo", display_label="Mongo", connection_config={})
        )

        all_sources = await repo.list_data_sources()

        assert len(all_sources) == 2

    @pytest.mark.asyncio
    async def test_update_data_source_applies_changes(self, async_session: AsyncSession):
        repo = DataSourceRepository(async_session)
        ds = await repo.create_data_source(
            DataSource(id=uuid4(), name="Old", source_type="pg", display_label="PG", connection_config={})
        )

        updated = await repo.update_data_source(ds.id, {"name": "New Name"})

        assert updated is not None
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_data_source_returns_none_when_not_found(self, async_session: AsyncSession):
        repo = DataSourceRepository(async_session)

        result = await repo.update_data_source(uuid4(), {"name": "Nope"})

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_data_source_removes_record(self, async_session: AsyncSession):
        repo = DataSourceRepository(async_session)
        ds = await repo.create_data_source(
            DataSource(id=uuid4(), name="Delete Me", source_type="pg", display_label="PG", connection_config={})
        )

        deleted = await repo.delete_data_source(ds.id)

        assert deleted is True
        assert await repo.get_data_source(ds.id) is None

    @pytest.mark.asyncio
    async def test_delete_data_source_returns_false_when_not_found(self, async_session: AsyncSession):
        repo = DataSourceRepository(async_session)

        deleted = await repo.delete_data_source(uuid4())

        assert deleted is False


# --- ConversationRepository Tests ---


class TestConversationRepository:
    """Tests for ConversationRepository CRUD and message operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_conversation(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = ConversationRepository(async_session)

        conv = await repo.create_conversation(
            Conversation(id=uuid4(), project_id=project.id, user_id=user.id, title="Test Chat")
        )
        fetched = await repo.get_conversation(conv.id)

        assert fetched is not None
        assert fetched.title == "Test Chat"

    @pytest.mark.asyncio
    async def test_list_by_project_returns_project_conversations(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = ConversationRepository(async_session)

        await repo.create_conversation(
            Conversation(id=uuid4(), project_id=project.id, user_id=user.id, title="Chat 1")
        )
        await repo.create_conversation(
            Conversation(id=uuid4(), project_id=project.id, user_id=user.id, title="Chat 2")
        )

        conversations = await repo.list_by_project(project.id)

        assert len(conversations) == 2

    @pytest.mark.asyncio
    async def test_delete_conversation_removes_record(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = ConversationRepository(async_session)

        conv = await repo.create_conversation(
            Conversation(id=uuid4(), project_id=project.id, user_id=user.id)
        )
        deleted = await repo.delete_conversation(conv.id)

        assert deleted is True
        assert await repo.get_conversation(conv.id) is None

    @pytest.mark.asyncio
    async def test_add_message_and_list_messages(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = ConversationRepository(async_session)

        conv = await repo.create_conversation(
            Conversation(id=uuid4(), project_id=project.id, user_id=user.id)
        )

        msg1 = await repo.add_message(
            Message(id=uuid4(), conversation_id=conv.id, role="user", content="Hello")
        )
        msg2 = await repo.add_message(
            Message(id=uuid4(), conversation_id=conv.id, role="assistant", content="Hi there")
        )

        messages = await repo.list_messages(conv.id)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"


# --- QueryHistoryRepository Tests ---


class TestQueryHistoryRepository:
    """Tests for QueryHistoryRepository — append-only and saved queries."""

    @pytest.mark.asyncio
    async def test_create_and_get_query_history(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        conv_repo = ConversationRepository(async_session)
        conv = await conv_repo.create_conversation(
            Conversation(id=uuid4(), project_id=project.id, user_id=user.id)
        )

        repo = QueryHistoryRepository(async_session)
        qh = await repo.create_query_history(
            QueryHistory(
                id=uuid4(),
                query_id=uuid4(),
                conversation_id=conv.id,
                project_id=project.id,
                question="What is revenue?",
            )
        )

        fetched = await repo.get_query_history(qh.id)

        assert fetched is not None
        assert fetched.question == "What is revenue?"

    @pytest.mark.asyncio
    async def test_list_by_project_orders_by_created_at_desc(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        conv_repo = ConversationRepository(async_session)
        conv = await conv_repo.create_conversation(
            Conversation(id=uuid4(), project_id=project.id, user_id=user.id)
        )

        repo = QueryHistoryRepository(async_session)
        # Explicit timestamps to guarantee ordering (SQLite may not differentiate sub-second inserts)
        earlier = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        later = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

        await repo.create_query_history(
            QueryHistory(
                id=uuid4(), query_id=uuid4(), conversation_id=conv.id,
                project_id=project.id, question="First question", created_at=earlier,
            )
        )
        await repo.create_query_history(
            QueryHistory(
                id=uuid4(), query_id=uuid4(), conversation_id=conv.id,
                project_id=project.id, question="Second question", created_at=later,
            )
        )

        results = await repo.list_by_project(project.id)

        assert len(results) == 2
        # Most recent first
        assert results[0].question == "Second question"
        assert results[1].question == "First question"

    @pytest.mark.asyncio
    async def test_query_history_has_no_delete_method(self, async_session: AsyncSession):
        """Verify append-only: QueryHistoryRepository does not expose delete for history records."""
        repo = QueryHistoryRepository(async_session)
        assert not hasattr(repo, "delete_query_history")

    @pytest.mark.asyncio
    async def test_create_and_delete_saved_query(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = QueryHistoryRepository(async_session)

        saved = await repo.create_saved_query(
            SavedQuery(
                id=uuid4(), user_id=user.id, project_id=project.id,
                title="Revenue Query", question="What is total revenue?",
            )
        )

        fetched = await repo.get_saved_query(saved.id)
        assert fetched is not None
        assert fetched.title == "Revenue Query"

        deleted = await repo.delete_saved_query(saved.id)
        assert deleted is True
        assert await repo.get_saved_query(saved.id) is None

    @pytest.mark.asyncio
    async def test_list_saved_by_project(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = QueryHistoryRepository(async_session)

        await repo.create_saved_query(
            SavedQuery(
                id=uuid4(), user_id=user.id, project_id=project.id,
                title="Q1", question="Question 1",
            )
        )
        await repo.create_saved_query(
            SavedQuery(
                id=uuid4(), user_id=user.id, project_id=project.id,
                title="Q2", question="Question 2",
            )
        )

        saved_queries = await repo.list_saved_by_project(project.id)

        assert len(saved_queries) == 2


# --- FileRepository Tests ---


class TestFileRepository:
    """Tests for FileRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_file(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = FileRepository(async_session)

        uploaded = await repo.create_file(
            UploadedFile(
                id=uuid4(),
                project_id=project.id,
                file_name="report.pdf",
                file_type="pdf",
                file_size=1024,
                uploaded_by=user.id,
            )
        )
        fetched = await repo.get_file(uploaded.id)

        assert fetched is not None
        assert fetched.file_name == "report.pdf"

    @pytest.mark.asyncio
    async def test_list_by_project_returns_project_files(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = FileRepository(async_session)

        await repo.create_file(
            UploadedFile(
                id=uuid4(), project_id=project.id, file_name="a.csv",
                file_type="csv", file_size=100, uploaded_by=user.id,
            )
        )
        await repo.create_file(
            UploadedFile(
                id=uuid4(), project_id=project.id, file_name="b.xlsx",
                file_type="xlsx", file_size=200, uploaded_by=user.id,
            )
        )

        files = await repo.list_by_project(project.id)

        assert len(files) == 2

    @pytest.mark.asyncio
    async def test_update_file_applies_changes(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = FileRepository(async_session)

        uploaded = await repo.create_file(
            UploadedFile(
                id=uuid4(), project_id=project.id, file_name="doc.pdf",
                file_type="pdf", file_size=500, uploaded_by=user.id,
            )
        )

        updated = await repo.update_file(uploaded.id, {"processing_status": "completed"})

        assert updated is not None
        assert updated.processing_status == "completed"

    @pytest.mark.asyncio
    async def test_update_file_returns_none_when_not_found(self, async_session: AsyncSession):
        repo = FileRepository(async_session)

        result = await repo.update_file(uuid4(), {"processing_status": "failed"})

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_file_removes_record(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        repo = FileRepository(async_session)

        uploaded = await repo.create_file(
            UploadedFile(
                id=uuid4(), project_id=project.id, file_name="temp.txt",
                file_type="txt", file_size=10, uploaded_by=user.id,
            )
        )

        deleted = await repo.delete_file(uploaded.id)

        assert deleted is True
        assert await repo.get_file(uploaded.id) is None


# --- SourceConnectionRepository Tests ---


class TestSourceConnectionRepository:
    """Tests for SourceConnectionRepository including duplicate handling."""

    @pytest.mark.asyncio
    async def test_create_connection_succeeds(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        ds = await create_test_data_source(async_session)
        repo = SourceConnectionRepository(async_session)

        conn = await repo.create_connection(
            SourceConnection(
                id=uuid4(), project_id=project.id,
                data_source_id=ds.id, purpose="analytics",
            )
        )

        assert conn.project_id == project.id
        assert conn.data_source_id == ds.id

    @pytest.mark.asyncio
    async def test_create_duplicate_connection_raises_error(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        ds = await create_test_data_source(async_session)
        repo = SourceConnectionRepository(async_session)

        await repo.create_connection(
            SourceConnection(
                id=uuid4(), project_id=project.id,
                data_source_id=ds.id, purpose="analytics",
            )
        )

        with pytest.raises(DuplicateSourceConnectionError):
            await repo.create_connection(
                SourceConnection(
                    id=uuid4(), project_id=project.id,
                    data_source_id=ds.id, purpose="duplicate attempt",
                )
            )

    @pytest.mark.asyncio
    async def test_delete_connection_removes_record(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        ds = await create_test_data_source(async_session)
        repo = SourceConnectionRepository(async_session)

        await repo.create_connection(
            SourceConnection(
                id=uuid4(), project_id=project.id,
                data_source_id=ds.id, purpose="analytics",
            )
        )

        deleted = await repo.delete_connection(project.id, ds.id)

        assert deleted is True
        connections = await repo.list_by_project(project.id)
        assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_delete_connection_returns_false_when_not_found(self, async_session: AsyncSession):
        repo = SourceConnectionRepository(async_session)

        deleted = await repo.delete_connection(uuid4(), uuid4())

        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_by_project_returns_connections(self, async_session: AsyncSession):
        user = await create_test_user(async_session)
        project = await create_test_project(async_session, user)
        ds1 = await create_test_data_source(async_session)
        ds2 = await create_test_data_source(async_session)
        repo = SourceConnectionRepository(async_session)

        await repo.create_connection(
            SourceConnection(id=uuid4(), project_id=project.id, data_source_id=ds1.id, purpose="p1")
        )
        await repo.create_connection(
            SourceConnection(id=uuid4(), project_id=project.id, data_source_id=ds2.id, purpose="p2")
        )

        connections = await repo.list_by_project(project.id)

        assert len(connections) == 2
