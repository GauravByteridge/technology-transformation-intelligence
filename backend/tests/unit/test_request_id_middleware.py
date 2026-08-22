"""Tests for the request ID middleware and ContextVar propagation."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_settings
from app.main import create_app
from app.middleware.request_id import request_id_ctx


@pytest.fixture
def app():
    """Create a fresh app instance for middleware tests."""
    get_settings.cache_clear()
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client for testing the middleware."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRequestIdMiddleware:
    """Verify request ID middleware generates and propagates UUID v4."""

    @pytest.mark.asyncio
    async def test_response_has_request_id_header(self, client) -> None:
        """Every response must include X-Request-ID header."""
        response = await client.get("/api/v1/health")
        assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    async def test_request_id_is_uuid_v4_format(self, client) -> None:
        """X-Request-ID must be a valid UUID v4."""
        import uuid

        response = await client.get("/api/v1/health")
        request_id = response.headers["x-request-id"]
        # Should not raise ValueError if it's a valid UUID
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4

    @pytest.mark.asyncio
    async def test_each_request_gets_unique_id(self, client) -> None:
        """Each request must get a distinct request_id."""
        response1 = await client.get("/api/v1/health")
        response2 = await client.get("/api/v1/health")
        id1 = response1.headers["x-request-id"]
        id2 = response2.headers["x-request-id"]
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_request_id_in_404_response(self, client) -> None:
        """Even error responses should carry the X-Request-ID header."""
        response = await client.get("/api/v1/nonexistent")
        assert "x-request-id" in response.headers


class TestRequestIdContextVar:
    """Verify the ContextVar stores the request_id correctly."""

    def test_context_var_default_is_empty(self) -> None:
        """Without a request, the ContextVar should return empty string."""
        assert request_id_ctx.get("") == ""
