"""
Tests for the layered architecture proof: API → Service → Repository.

Verifies the full GET /api/v1/projects/{id} chain including:
- Valid UUID returns project data (200)
- Unknown UUID returns 404 with structured error
- Invalid UUID format returns 422 with validation error
- Dependency injection wiring works end-to-end
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_app_db_session, get_settings
from app.main import create_app
from app.models.project import Project


def _make_project(
    project_id: str = "11111111-1111-1111-1111-111111111111",
    name: str = "Alpha Transformation",
    description: str = "Enterprise modernization initiative",
    status: str = "active",
) -> Project:
    """Create a Project model instance for testing."""
    return Project(
        id=UUID(project_id),
        name=name,
        description=description,
        status=status,
        created_by=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 6, 1, 14, 30, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession for repository testing."""
    session = AsyncMock()
    return session


@pytest.fixture
def app(mock_session):
    """Create a fresh app instance with mocked database session."""
    get_settings.cache_clear()
    application = create_app()

    async def _override_session():
        yield mock_session

    application.dependency_overrides[get_app_db_session] = _override_session
    return application


@pytest_asyncio.fixture
async def client(app, mock_session):
    """Async HTTP client for testing project endpoints."""
    # Configure mock_session.get to return the test project for the known ID
    async def mock_get(model_class, entity_id):
        if entity_id == UUID("11111111-1111-1111-1111-111111111111"):
            return _make_project()
        return None

    mock_session.get = mock_get

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestGetProjectEndpoint:
    """Verify GET /api/v1/projects/{project_id} works end-to-end."""

    EXISTING_PROJECT_ID = "11111111-1111-1111-1111-111111111111"
    NONEXISTENT_PROJECT_ID = "99999999-9999-9999-9999-999999999999"
    INVALID_ID = "not-a-uuid"

    @pytest.mark.asyncio
    async def test_get_project_returns_200_for_existing_project(self, client) -> None:
        response = await client.get(f"/api/v1/projects/{self.EXISTING_PROJECT_ID}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_project_returns_correct_data(self, client) -> None:
        response = await client.get(f"/api/v1/projects/{self.EXISTING_PROJECT_ID}")
        body = response.json()
        assert body["id"] == self.EXISTING_PROJECT_ID
        assert body["name"] == "Alpha Transformation"
        assert body["status"] == "active"
        assert body["description"] == "Enterprise modernization initiative"

    @pytest.mark.asyncio
    async def test_get_project_response_includes_timestamps(self, client) -> None:
        response = await client.get(f"/api/v1/projects/{self.EXISTING_PROJECT_ID}")
        body = response.json()
        assert "created_at" in body
        assert "updated_at" in body

    @pytest.mark.asyncio
    async def test_get_project_returns_404_for_nonexistent_project(self, client) -> None:
        response = await client.get(f"/api/v1/projects/{self.NONEXISTENT_PROJECT_ID}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_404_returns_structured_error(self, client) -> None:
        response = await client.get(f"/api/v1/projects/{self.NONEXISTENT_PROJECT_ID}")
        body = response.json()
        assert body["error_code"] == "PROJECT_NOT_FOUND"
        assert "request_id" in body
        assert "message" in body

    @pytest.mark.asyncio
    async def test_get_project_returns_422_for_invalid_uuid(self, client) -> None:
        response = await client.get(f"/api/v1/projects/{self.INVALID_ID}")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_project_includes_request_id_header(self, client) -> None:
        response = await client.get(f"/api/v1/projects/{self.EXISTING_PROJECT_ID}")
        assert "x-request-id" in response.headers


class TestProjectService:
    """Unit tests for ProjectService in isolation."""

    @pytest.mark.asyncio
    async def test_service_returns_project_response(self) -> None:
        from app.repositories.project_repository import ProjectRepository
        from app.services.project_service import ProjectService

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=_make_project())

        repo = ProjectRepository(mock_session)
        service = ProjectService(repository=repo)
        result = await service.get_project(UUID("11111111-1111-1111-1111-111111111111"))

        assert result.name == "Alpha Transformation"
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_service_raises_not_found_for_unknown_id(self) -> None:
        from app.errors.project_errors import ProjectNotFoundError
        from app.repositories.project_repository import ProjectRepository
        from app.services.project_service import ProjectService

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        repo = ProjectRepository(mock_session)
        service = ProjectService(repository=repo)

        with pytest.raises(ProjectNotFoundError):
            await service.get_project(UUID("99999999-9999-9999-9999-999999999999"))


class TestProjectRepository:
    """Unit tests for ProjectRepository in isolation."""

    @pytest.mark.asyncio
    async def test_repository_returns_project_for_existing_id(self) -> None:
        from app.repositories.project_repository import ProjectRepository

        mock_session = AsyncMock()
        expected_project = _make_project()
        mock_session.get = AsyncMock(return_value=expected_project)

        repo = ProjectRepository(mock_session)
        result = await repo.get_project(UUID("11111111-1111-1111-1111-111111111111"))

        assert result is not None
        assert result.name == "Alpha Transformation"

    @pytest.mark.asyncio
    async def test_repository_returns_none_for_unknown_id(self) -> None:
        from app.repositories.project_repository import ProjectRepository

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        repo = ProjectRepository(mock_session)
        result = await repo.get_project(UUID("99999999-9999-9999-9999-999999999999"))

        assert result is None
