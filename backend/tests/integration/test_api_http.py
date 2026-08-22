"""
HTTP-level integration tests using httpx AsyncClient against the actual FastAPI app.

Tests exercise the full path: HTTP route → FastAPI Depends → Service → Repository → SQLite.
The app's get_app_db_session and get_settings dependencies are overridden to use an
in-memory SQLite session and a test FERNET_KEY respectively.

These tests validate:
- Project CRUD (201, 200, 204, 404)
- Data source CRUD with credential masking verification
- Source connection creation (201, project 404, data_source 404, duplicate 409)
- Conversation creation (201, project not found 404)
- File creation (201, project not found 404, data_source not found 404)
- Query history creation (201, append-only: no PATCH/DELETE returns 405)
- Missing entity → correct 404 with structured error response
"""

import uuid
from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import AppBase
from app.models.user import User


# Test Fernet key for settings override
TEST_FERNET_KEY = Fernet.generate_key().decode()

# Use a proper uuid4 to avoid Python 3.14 SQLite UUID storage edge case
# with the all-zeros UUID constant (00000000-0000-0000-0000-000000000001)
TEST_SYSTEM_USER_ID = uuid4()


@pytest_asyncio.fixture
async def async_client():
    """
    Provide an httpx AsyncClient wired to the FastAPI app with SQLite overrides.

    Overrides:
    - get_app_db_session → yields sessions from in-memory SQLite
    - get_settings → returns Settings with test FERNET_KEY
    - SYSTEM_USER_ID patched in all service modules to use a uuid4() value
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key enforcement in SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(AppBase.metadata.create_all)

    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Seed the test system user so FK constraints on user_id/created_by succeed
    async with async_session_factory() as session:
        system_user = User(
            id=TEST_SYSTEM_USER_ID,
            email="system@test.local",
            name="System User",
            role="system",
        )
        session.add(system_user)
        await session.commit()

    # Session dependency override
    async def override_get_app_db_session():
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # Settings override with test FERNET_KEY
    def override_get_settings():
        from app.config.settings import Settings

        return Settings(
            app_db_url="sqlite+aiosqlite://",
            secret_key="test-secret",
            fernet_key=TEST_FERNET_KEY,
            demo_mode=True,
        )

    # Import and create app fresh for test isolation
    from app.dependencies import get_app_db_session, get_settings
    from app.main import create_app

    # Patch SYSTEM_USER_ID in all service modules that import it by value
    with (
        patch("app.services.project_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID),
        patch("app.services.conversation_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID),
        patch("app.services.file_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID),
        patch("app.services.query_history_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID),
    ):
        app = create_app()
        app.dependency_overrides[get_app_db_session] = override_get_app_db_session
        app.dependency_overrides[get_settings] = override_get_settings

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(AppBase.metadata.drop_all)
    await engine.dispose()


# =============================================================================
# Project CRUD Tests
# =============================================================================


class TestProjectCRUD:
    """Full project lifecycle via HTTP."""

    @pytest.mark.asyncio
    async def test_create_project_returns_201(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "A test project"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_project_returns_200(self, async_client: AsyncClient):
        create_resp = await async_client.post(
            "/api/v1/projects",
            json={"name": "Get Me"},
        )
        project_id = create_resp.json()["id"]

        response = await async_client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Me"

    @pytest.mark.asyncio
    async def test_list_projects_returns_200(self, async_client: AsyncClient):
        await async_client.post("/api/v1/projects", json={"name": "P1"})
        await async_client.post("/api/v1/projects", json={"name": "P2"})

        response = await async_client.get("/api/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_update_project_returns_200(self, async_client: AsyncClient):
        create_resp = await async_client.post(
            "/api/v1/projects", json={"name": "Original"}
        )
        project_id = create_resp.json()["id"]

        response = await async_client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_project_returns_204(self, async_client: AsyncClient):
        create_resp = await async_client.post(
            "/api/v1/projects", json={"name": "Delete Me"}
        )
        project_id = create_resp.json()["id"]

        response = await async_client.delete(f"/api/v1/projects/{project_id}")
        assert response.status_code == 204

        # Verify gone
        get_resp = await async_client.get(f"/api/v1/projects/{project_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_project_returns_404(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/projects/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "PROJECT_NOT_FOUND"


# =============================================================================
# Data Source CRUD with Credential Masking Tests
# =============================================================================


class TestDataSourceCRUD:
    """Data source lifecycle with credential masking verification."""

    @pytest.mark.asyncio
    async def test_create_data_source_returns_201(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/data-sources",
            json={
                "name": "Test DB",
                "source_type": "postgresql",
                "display_label": "Test PostgreSQL",
                "connection_config": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "testdb",
                    "password": "supersecret",
                },
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test DB"
        assert data["source_type"] == "postgresql"

    @pytest.mark.asyncio
    async def test_credential_masking_on_create(self, async_client: AsyncClient):
        """POST response must have *_configured, never plaintext password."""
        response = await async_client.post(
            "/api/v1/data-sources",
            json={
                "name": "Masked DB",
                "source_type": "postgresql",
                "display_label": "Masked PG",
                "connection_config": {
                    "host": "db.example.com",
                    "port": 5432,
                    "password": "my-secret-password",
                },
            },
        )
        assert response.status_code == 201
        config = response.json()["connection_config"]

        # Sensitive field is masked as boolean indicator
        assert config["password_configured"] is True
        # Plaintext password never appears
        assert "password" not in config
        assert "my-secret-password" not in str(config)
        # Non-sensitive fields preserved
        assert config["host"] == "db.example.com"
        assert config["port"] == 5432

    @pytest.mark.asyncio
    async def test_credential_masking_on_get(self, async_client: AsyncClient):
        """GET response must mask credentials identically."""
        create_resp = await async_client.post(
            "/api/v1/data-sources",
            json={
                "name": "Get Masked",
                "source_type": "mongodb",
                "display_label": "Get Masked Mongo",
                "connection_config": {
                    "host": "mongo.example.com",
                    "token": "secret-token-value",
                    "api_key": "secret-api-key",
                },
            },
        )
        ds_id = create_resp.json()["id"]

        response = await async_client.get(f"/api/v1/data-sources/{ds_id}")
        assert response.status_code == 200
        config = response.json()["connection_config"]

        assert config["token_configured"] is True
        assert config["api_key_configured"] is True
        assert "token" not in config
        assert "api_key" not in config
        assert "secret-token-value" not in str(config)
        assert "secret-api-key" not in str(config)
        assert config["host"] == "mongo.example.com"

    @pytest.mark.asyncio
    async def test_update_data_source_returns_200(self, async_client: AsyncClient):
        create_resp = await async_client.post(
            "/api/v1/data-sources",
            json={
                "name": "Update Me",
                "source_type": "postgresql",
                "display_label": "Update PG",
                "connection_config": {"host": "old-host"},
            },
        )
        ds_id = create_resp.json()["id"]

        response = await async_client.patch(
            f"/api/v1/data-sources/{ds_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_data_source_returns_204(self, async_client: AsyncClient):
        create_resp = await async_client.post(
            "/api/v1/data-sources",
            json={
                "name": "Delete DS",
                "source_type": "postgresql",
                "display_label": "Delete PG",
                "connection_config": {},
            },
        )
        ds_id = create_resp.json()["id"]

        response = await async_client.delete(f"/api/v1/data-sources/{ds_id}")
        assert response.status_code == 204

        # Verify gone
        get_resp = await async_client.get(f"/api/v1/data-sources/{ds_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_data_source_returns_404(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/data-sources/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "DATA_SOURCE_NOT_FOUND"


# =============================================================================
# Source Connection Tests
# =============================================================================


class TestSourceConnections:
    """Source connection (project-to-data-source relationship) HTTP tests."""

    async def _create_project(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/projects", json={"name": "SC Project"})
        return resp.json()["id"]

    async def _create_data_source(self, client: AsyncClient) -> str:
        resp = await client.post(
            "/api/v1/data-sources",
            json={
                "name": "SC DataSource",
                "source_type": "postgresql",
                "display_label": "SC PG",
                "connection_config": {"host": "localhost"},
            },
        )
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_create_source_connection_returns_201(self, async_client: AsyncClient):
        project_id = await self._create_project(async_client)
        ds_id = await self._create_data_source(async_client)

        response = await async_client.post(
            f"/api/v1/projects/{project_id}/data-sources",
            json={"data_source_id": ds_id, "purpose": "Finance data"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == project_id
        assert data["data_source_id"] == ds_id
        assert data["purpose"] == "Finance data"

    @pytest.mark.asyncio
    async def test_source_connection_project_not_found_returns_404(
        self, async_client: AsyncClient
    ):
        ds_id = await self._create_data_source(async_client)
        fake_project_id = str(uuid.uuid4())

        response = await async_client.post(
            f"/api/v1/projects/{fake_project_id}/data-sources",
            json={"data_source_id": ds_id, "purpose": "Test"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "PROJECT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_source_connection_data_source_not_found_returns_404(
        self, async_client: AsyncClient
    ):
        project_id = await self._create_project(async_client)
        fake_ds_id = str(uuid.uuid4())

        response = await async_client.post(
            f"/api/v1/projects/{project_id}/data-sources",
            json={"data_source_id": fake_ds_id, "purpose": "Test"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "DATA_SOURCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_duplicate_source_connection_returns_409(self, async_client: AsyncClient):
        project_id = await self._create_project(async_client)
        ds_id = await self._create_data_source(async_client)

        # First connection succeeds
        resp1 = await async_client.post(
            f"/api/v1/projects/{project_id}/data-sources",
            json={"data_source_id": ds_id, "purpose": "First"},
        )
        assert resp1.status_code == 201

        # Duplicate should be 409
        resp2 = await async_client.post(
            f"/api/v1/projects/{project_id}/data-sources",
            json={"data_source_id": ds_id, "purpose": "Second"},
        )
        assert resp2.status_code == 409
        assert resp2.json()["error_code"] == "DUPLICATE_SOURCE_CONNECTION"


# =============================================================================
# Conversation Tests
# =============================================================================


class TestConversations:
    """Conversation creation and project existence validation."""

    async def _create_project(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/projects", json={"name": "Conv Project"})
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_create_conversation_returns_201(self, async_client: AsyncClient):
        project_id = await self._create_project(async_client)

        response = await async_client.post(
            "/api/v1/conversations",
            json={"project_id": project_id, "title": "Test Conversation"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == project_id
        assert data["title"] == "Test Conversation"
        assert data["user_id"] == str(TEST_SYSTEM_USER_ID)

    @pytest.mark.asyncio
    async def test_create_conversation_project_not_found_returns_404(
        self, async_client: AsyncClient
    ):
        fake_project_id = str(uuid.uuid4())

        response = await async_client.post(
            "/api/v1/conversations",
            json={"project_id": fake_project_id, "title": "Orphan"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "PROJECT_NOT_FOUND"


# =============================================================================
# File Tests
# =============================================================================


class TestFiles:
    """File metadata creation with project/data_source validation."""

    async def _create_project(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/projects", json={"name": "File Project"})
        return resp.json()["id"]

    async def _create_data_source(self, client: AsyncClient) -> str:
        resp = await client.post(
            "/api/v1/data-sources",
            json={
                "name": "File DS",
                "source_type": "postgresql",
                "display_label": "File PG",
                "connection_config": {},
            },
        )
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_create_file_returns_201(self, async_client: AsyncClient):
        project_id = await self._create_project(async_client)

        response = await async_client.post(
            "/api/v1/files",
            json={
                "project_id": project_id,
                "file_name": "report.pdf",
                "file_type": "application/pdf",
                "file_size": 1024,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "report.pdf"
        assert data["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_create_file_project_not_found_returns_404(
        self, async_client: AsyncClient
    ):
        fake_project_id = str(uuid.uuid4())

        response = await async_client.post(
            "/api/v1/files",
            json={
                "project_id": fake_project_id,
                "file_name": "orphan.txt",
                "file_type": "text/plain",
                "file_size": 100,
            },
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "PROJECT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_file_data_source_not_found_returns_404(
        self, async_client: AsyncClient
    ):
        project_id = await self._create_project(async_client)
        fake_ds_id = str(uuid.uuid4())

        response = await async_client.post(
            "/api/v1/files",
            json={
                "project_id": project_id,
                "data_source_id": fake_ds_id,
                "file_name": "bad-ds.csv",
                "file_type": "text/csv",
                "file_size": 200,
            },
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "DATA_SOURCE_NOT_FOUND"


# =============================================================================
# Query History Tests
# =============================================================================


class TestQueryHistory:
    """Query history append-only enforcement and creation."""

    async def _create_project(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/projects", json={"name": "QH Project"})
        return resp.json()["id"]

    async def _create_conversation(self, client: AsyncClient, project_id: str) -> str:
        resp = await client.post(
            "/api/v1/conversations",
            json={"project_id": project_id, "title": "QH Conversation"},
        )
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_create_query_history_returns_201(self, async_client: AsyncClient):
        project_id = await self._create_project(async_client)
        conversation_id = await self._create_conversation(async_client, project_id)

        response = await async_client.post(
            "/api/v1/query-history",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id,
                "query_id": str(uuid.uuid4()),
                "question": "What is the revenue?",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["question"] == "What is the revenue?"
        assert data["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_query_history_patch_returns_405(self, async_client: AsyncClient):
        """Query history is append-only — PATCH should return 405."""
        project_id = await self._create_project(async_client)
        conversation_id = await self._create_conversation(async_client, project_id)

        create_resp = await async_client.post(
            "/api/v1/query-history",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id,
                "query_id": str(uuid.uuid4()),
                "question": "Append only question",
            },
        )
        qh_id = create_resp.json()["id"]

        # PATCH not allowed
        response = await async_client.patch(
            f"/api/v1/query-history/{qh_id}",
            json={"question": "Modified"},
        )
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_query_history_delete_returns_405(self, async_client: AsyncClient):
        """Query history is append-only — DELETE should return 405."""
        project_id = await self._create_project(async_client)
        conversation_id = await self._create_conversation(async_client, project_id)

        create_resp = await async_client.post(
            "/api/v1/query-history",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id,
                "query_id": str(uuid.uuid4()),
                "question": "Should not be deleted",
            },
        )
        qh_id = create_resp.json()["id"]

        # DELETE not allowed
        response = await async_client.delete(f"/api/v1/query-history/{qh_id}")
        assert response.status_code == 405


# =============================================================================
# Missing Entity → Structured 404 Response
# =============================================================================


class TestStructured404:
    """Verifies all missing entity paths return structured error responses."""

    @pytest.mark.asyncio
    async def test_missing_project_structured_error(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/projects/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_missing_data_source_structured_error(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/data-sources/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_missing_conversation_structured_error(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/conversations/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_missing_file_structured_error(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/files/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_missing_query_history_structured_error(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/query-history/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data
