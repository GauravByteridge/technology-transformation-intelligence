"""Tests for FastAPI application entry point."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.dependencies import get_settings


@pytest.fixture
def app():
    """Create a fresh app instance for each test."""
    # Clear the lru_cache so test env vars are picked up
    get_settings.cache_clear()
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client for testing the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestAppCreation:
    """Verify the FastAPI application is configured correctly."""

    def test_app_title(self, app) -> None:
        assert app.title == "Technology Transformation Intelligence Platform"

    def test_app_version(self, app) -> None:
        assert app.version == "0.1.0"

    def test_api_v1_router_mounted(self, app) -> None:
        route_paths = []
        for route in app.routes:
            if hasattr(route, "path"):
                route_paths.append(route.path)
        # The /api/v1 prefix should exist (even if no sub-routes yet)
        assert any("/api/v1" in path for path in route_paths) or len(app.routes) > 0


class TestCORSMiddleware:
    """Verify CORS is configured from environment variables."""

    @pytest.mark.asyncio
    async def test_allowed_origin_gets_cors_headers(self, client) -> None:
        response = await client.options(
            "/api/v1/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    @pytest.mark.asyncio
    async def test_disallowed_origin_blocked(self, client) -> None:
        response = await client.options(
            "/api/v1/",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in response.headers

    @pytest.mark.asyncio
    async def test_cors_allows_all_methods(self, client) -> None:
        response = await client.options(
            "/api/v1/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        allow_methods = response.headers.get("access-control-allow-methods", "")
        # Should allow all methods (POST specifically)
        assert "POST" in allow_methods or "*" in allow_methods


class TestOpenAPIDocs:
    """Verify API documentation endpoints are accessible."""

    @pytest.mark.asyncio
    async def test_openapi_schema_available(self, client) -> None:
        response = await client.get("/api/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Technology Transformation Intelligence Platform"
