"""Tests for the health check endpoint."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_settings
from app.main import create_app


@pytest.fixture
def app():
    """Create a fresh app instance for health check tests."""
    get_settings.cache_clear()
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client for testing the health endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Verify the /api/v1/health endpoint works correctly."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_returns_status_ok(self, client) -> None:
        response = await client.get("/api/v1/health")
        body = response.json()
        assert body["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_response_includes_request_id_header(self, client) -> None:
        response = await client.get("/api/v1/health")
        assert "x-request-id" in response.headers
        # Verify it's a valid UUID format (36 characters with dashes)
        request_id = response.headers["x-request-id"]
        assert len(request_id) == 36
        assert request_id.count("-") == 4
