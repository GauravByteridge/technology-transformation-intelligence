"""Tests for API route endpoints added in Task 13.1, 13.2, 13.3."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.ai.service import AIService
from app.connectors.registry import ConnectorRegistry
from app.dependencies import get_ai_service, get_app_db_session, get_connector_registry, get_settings
from app.main import create_app
from app.schemas.ai import AIResponse


@pytest.fixture
def mock_ai_service():
    """Create a mock AIService for dependency injection."""
    service = AsyncMock(spec=AIService)
    service.execute_query = AsyncMock(
        return_value=AIResponse(
            answer="This is a test response.",
            response_type="text",
            sources=[],
            evidence=[],
            query_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            is_partial=False,
            failed_sources=[],
        )
    )
    return service


@pytest.fixture
def mock_connector_registry():
    """Create a mock ConnectorRegistry for dependency injection."""
    registry = MagicMock(spec=ConnectorRegistry)
    return registry


@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def app(mock_ai_service, mock_connector_registry, mock_db_session):
    """Create a fresh app instance with dependency overrides for route tests."""
    get_settings.cache_clear()
    application = create_app()

    # Override dependencies that require lifespan initialization
    application.dependency_overrides[get_ai_service] = lambda: mock_ai_service
    application.dependency_overrides[get_connector_registry] = lambda: mock_connector_registry
    application.dependency_overrides[get_app_db_session] = lambda: mock_db_session

    yield application

    # Clean up overrides
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client for testing endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestDataSourceTestConnection:
    """Tests for POST /api/v1/data-sources/{id}/test-connection."""

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_source(self, client, mock_db_session) -> None:
        """Non-existent data source should return 404."""
        fake_id = str(uuid.uuid4())

        # Mock the repository to return None (not found)
        with patch(
            "app.api.v1.data_sources.DataSourceRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_data_source = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            response = await client.post(f"/api/v1/data-sources/{fake_id}/test-connection")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_422_for_invalid_uuid(self, client) -> None:
        """Invalid UUID format should return 422."""
        response = await client.post("/api/v1/data-sources/not-a-uuid/test-connection")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_successful_connection_test(self, client, mock_connector_registry, mock_db_session) -> None:
        """Successful connection test returns structured response."""
        fake_id = uuid.uuid4()

        # Mock data source
        mock_data_source = MagicMock()
        mock_data_source.id = fake_id
        mock_data_source.name = "Test DB"
        mock_data_source.source_type = "postgresql"
        mock_data_source.connection_config = {"host": "localhost"}

        # Mock connector
        mock_connector = AsyncMock()
        mock_connector.test_connection = AsyncMock(return_value=True)
        mock_connector_registry.resolve.return_value = mock_connector

        with patch(
            "app.api.v1.data_sources.DataSourceRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_data_source = AsyncMock(return_value=mock_data_source)
            mock_repo_cls.return_value = mock_repo

            response = await client.post(
                f"/api/v1/data-sources/{fake_id}/test-connection"
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["source_type"] == "postgresql"
        assert body["source_name"] == "Test DB"
        assert body["message"] == "Connection successful"
        assert "request_id" in body

    @pytest.mark.asyncio
    async def test_failed_connection_test(self, client, mock_connector_registry, mock_db_session) -> None:
        """Failed connection test returns success=false."""
        fake_id = uuid.uuid4()

        mock_data_source = MagicMock()
        mock_data_source.id = fake_id
        mock_data_source.name = "Broken DB"
        mock_data_source.source_type = "mongodb"
        mock_data_source.connection_config = {"url": "mongodb://bad"}

        mock_connector = AsyncMock()
        mock_connector.test_connection = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )
        mock_connector_registry.resolve.return_value = mock_connector

        with patch(
            "app.api.v1.data_sources.DataSourceRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_data_source = AsyncMock(return_value=mock_data_source)
            mock_repo_cls.return_value = mock_repo

            response = await client.post(
                f"/api/v1/data-sources/{fake_id}/test-connection"
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["message"] == "Connection failed"

    @pytest.mark.asyncio
    async def test_response_includes_request_id(self, client, mock_connector_registry, mock_db_session) -> None:
        """Response should include request_id in body."""
        fake_id = uuid.uuid4()

        mock_data_source = MagicMock()
        mock_data_source.id = fake_id
        mock_data_source.name = "Test DB"
        mock_data_source.source_type = "postgresql"
        mock_data_source.connection_config = {}

        mock_connector = AsyncMock()
        mock_connector.test_connection = AsyncMock(return_value=True)
        mock_connector_registry.resolve.return_value = mock_connector

        with patch(
            "app.api.v1.data_sources.DataSourceRepository"
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_data_source = AsyncMock(return_value=mock_data_source)
            mock_repo_cls.return_value = mock_repo

            response = await client.post(
                f"/api/v1/data-sources/{fake_id}/test-connection"
            )

        assert response.status_code == 200
        body = response.json()
        assert body["request_id"] != ""


class TestAIQueryEndpoint:
    """Tests for POST /api/v1/ai/query."""

    @pytest.mark.asyncio
    async def test_returns_422_for_missing_question(self, client) -> None:
        """Missing required fields should return 422."""
        response = await client.post("/api/v1/ai/query", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_422_for_empty_question(self, client) -> None:
        """Empty question string should fail validation."""
        response = await client.post(
            "/api/v1/ai/query",
            json={
                "question": "",
                "project_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_accepts_valid_query(self, client, mock_ai_service) -> None:
        """Valid AI query returns a structured response."""
        project_id = str(uuid.uuid4())

        response = await client.post(
            "/api/v1/ai/query",
            json={
                "question": "What is the project status?",
                "project_id": project_id,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert "answer" in body
        assert "response_type" in body
        assert "query_id" in body
        assert "conversation_id" in body
        assert body["response_type"] in ("text", "table", "chart")

    @pytest.mark.asyncio
    async def test_delegates_to_ai_service(self, client, mock_ai_service) -> None:
        """Route should delegate to AIService.execute_query()."""
        project_id = str(uuid.uuid4())

        await client.post(
            "/api/v1/ai/query",
            json={
                "question": "Test question",
                "project_id": project_id,
            },
        )

        mock_ai_service.execute_query.assert_called_once()
        call_kwargs = mock_ai_service.execute_query.call_args[1]
        assert call_kwargs["question"] == "Test question"

    @pytest.mark.asyncio
    async def test_response_includes_request_id_header(self, client) -> None:
        """Response should include X-Request-ID header."""
        response = await client.post(
            "/api/v1/ai/query",
            json={
                "question": "Test question",
                "project_id": str(uuid.uuid4()),
            },
        )
        assert "x-request-id" in response.headers


class TestDocumentUpload:
    """Tests for POST /api/v1/documents/upload."""

    @pytest.mark.asyncio
    async def test_upload_without_file_returns_accepted(self, client) -> None:
        """Upload endpoint works even without a file (stub behavior)."""
        response = await client.post("/api/v1/documents/upload")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "accepted"
        assert "request_id" in body

    @pytest.mark.asyncio
    async def test_upload_response_includes_request_id_header(self, client) -> None:
        """Response header includes X-Request-ID for traceability."""
        response = await client.post("/api/v1/documents/upload")
        assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    async def test_upload_message_contains_filename(self, client) -> None:
        """Response message should reference the uploaded file."""
        response = await client.post("/api/v1/documents/upload")
        body = response.json()
        assert "message" in body
        # Without a file, message says "no file provided"
        assert "no file provided" in body["message"]


class TestConfigMode:
    """Tests for GET /api/v1/config/mode (Task 13.2)."""

    @pytest.mark.asyncio
    async def test_returns_demo_mode_by_default(self, client) -> None:
        """Default configuration returns demo mode."""
        response = await client.get("/api/v1/config/mode")
        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "demo"
        assert body["demo_mode"] is True
        assert "request_id" in body

    @pytest.mark.asyncio
    async def test_response_includes_request_id_header(self, client) -> None:
        """Response should include X-Request-ID header."""
        response = await client.get("/api/v1/config/mode")
        assert "x-request-id" in response.headers
