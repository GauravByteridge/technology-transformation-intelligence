"""Tests for the error handling foundation."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_settings
from app.errors import (
    AIQueryError,
    AppError,
    ChunkingError,
    ConfigurationError,
    ContentExtractionError,
    DataSourceConnectionError,
    DocumentValidationError,
    EmbeddingGenerationError,
    ProjectNotFoundError,
    ProjectValidationError,
    ProviderCredentialError,
    ProviderResolutionError,
    QueryExecutionError,
    SchemaDiscoveryError,
    UnsupportedDataSourceError,
)
from app.errors.base import ErrorCategory, ERROR_CATEGORY_STATUS_MAP


class TestErrorCategoryMapping:
    """Verify error categories map to correct HTTP status codes."""

    def test_not_found_maps_to_404(self) -> None:
        assert ERROR_CATEGORY_STATUS_MAP[ErrorCategory.NOT_FOUND] == 404

    def test_validation_maps_to_422(self) -> None:
        assert ERROR_CATEGORY_STATUS_MAP[ErrorCategory.VALIDATION] == 422

    def test_authentication_maps_to_401(self) -> None:
        assert ERROR_CATEGORY_STATUS_MAP[ErrorCategory.AUTHENTICATION] == 401

    def test_authorization_maps_to_403(self) -> None:
        assert ERROR_CATEGORY_STATUS_MAP[ErrorCategory.AUTHORIZATION] == 403

    def test_conflict_maps_to_409(self) -> None:
        assert ERROR_CATEGORY_STATUS_MAP[ErrorCategory.CONFLICT] == 409

    def test_connection_maps_to_502(self) -> None:
        assert ERROR_CATEGORY_STATUS_MAP[ErrorCategory.CONNECTION] == 502

    def test_external_maps_to_502(self) -> None:
        assert ERROR_CATEGORY_STATUS_MAP[ErrorCategory.EXTERNAL] == 502

    def test_unhandled_maps_to_500(self) -> None:
        assert ERROR_CATEGORY_STATUS_MAP[ErrorCategory.UNHANDLED] == 500


class TestAppErrorBase:
    """Verify AppError base class behavior."""

    def test_app_error_stores_fields(self) -> None:
        error = AppError(
            error_code="TEST_ERROR",
            message="Something went wrong",
            domain="test",
            category=ErrorCategory.VALIDATION,
            detail="Extra context",
        )
        assert error.error_code == "TEST_ERROR"
        assert error.message == "Something went wrong"
        assert error.domain == "test"
        assert error.category == ErrorCategory.VALIDATION
        assert error.detail == "Extra context"

    def test_http_status_code_property(self) -> None:
        error = AppError(
            error_code="TEST",
            message="test",
            domain="test",
            category=ErrorCategory.NOT_FOUND,
        )
        assert error.http_status_code == 404

    def test_default_category_is_unhandled(self) -> None:
        error = AppError(error_code="X", message="x", domain="x")
        assert error.category == ErrorCategory.UNHANDLED
        assert error.http_status_code == 500

    def test_is_exception(self) -> None:
        error = AppError(error_code="X", message="test message", domain="x")
        assert isinstance(error, Exception)
        assert str(error) == "test message"


class TestProjectErrors:
    """Verify project domain error types."""

    def test_project_not_found_error(self) -> None:
        error = ProjectNotFoundError(project_id="abc-123")
        assert error.error_code == "PROJECT_NOT_FOUND"
        assert "abc-123" in error.message
        assert error.domain == "project"
        assert error.http_status_code == 404

    def test_project_validation_error(self) -> None:
        error = ProjectValidationError(message="Name is required")
        assert error.error_code == "PROJECT_VALIDATION_ERROR"
        assert error.message == "Name is required"
        assert error.domain == "project"
        assert error.http_status_code == 422


class TestDataSourceErrors:
    """Verify data source domain error types."""

    def test_connection_error(self) -> None:
        error = DataSourceConnectionError(
            source_type="postgresql",
            message="Connection refused",
        )
        assert error.error_code == "DATA_SOURCE_CONNECTION_ERROR"
        assert error.source_type == "postgresql"
        assert error.http_status_code == 502

    def test_schema_discovery_error(self) -> None:
        error = SchemaDiscoveryError(
            source_type="mongodb",
            message="Failed to list collections",
        )
        assert error.error_code == "SCHEMA_DISCOVERY_ERROR"
        assert error.source_type == "mongodb"
        assert error.http_status_code == 502

    def test_query_execution_error(self) -> None:
        error = QueryExecutionError(
            source_type="postgresql",
            message="Query timeout",
        )
        assert error.error_code == "QUERY_EXECUTION_ERROR"
        assert error.http_status_code == 502

    def test_unsupported_data_source_error(self) -> None:
        error = UnsupportedDataSourceError(
            requested_type="oracle",
            supported_types=["postgresql", "mongodb"],
        )
        assert error.error_code == "UNSUPPORTED_DATA_SOURCE"
        assert "oracle" in error.message
        assert "postgresql" in error.message
        assert error.http_status_code == 422


class TestDocumentErrors:
    """Verify document domain error types."""

    def test_document_validation_error(self) -> None:
        error = DocumentValidationError(
            file_name="bad.exe",
            message="Unsupported file format",
        )
        assert error.error_code == "DOCUMENT_VALIDATION_ERROR"
        assert error.file_name == "bad.exe"
        assert error.http_status_code == 422

    def test_content_extraction_error(self) -> None:
        error = ContentExtractionError(
            file_name="corrupt.pdf",
            message="Failed to extract text",
        )
        assert error.error_code == "CONTENT_EXTRACTION_ERROR"
        assert error.http_status_code == 502

    def test_chunking_error(self) -> None:
        error = ChunkingError(
            file_name="big.txt",
            message="Chunking strategy failed",
        )
        assert error.error_code == "CHUNKING_ERROR"
        assert error.http_status_code == 502

    def test_embedding_generation_error(self) -> None:
        error = EmbeddingGenerationError(file_name="report.pdf", message="Provider timeout")
        assert error.error_code == "EMBEDDING_GENERATION_ERROR"
        assert error.http_status_code == 502
        assert error.file_name == "report.pdf"


class TestAIErrors:
    """Verify AI domain error types."""

    def test_provider_resolution_error(self) -> None:
        error = ProviderResolutionError(
            provider_name="unknown",
            supported_providers=["azure_openai", "groq"],
        )
        assert error.error_code == "PROVIDER_RESOLUTION_ERROR"
        assert "unknown" in error.message
        assert error.http_status_code == 422

    def test_provider_credential_error(self) -> None:
        error = ProviderCredentialError(
            provider_name="azure_openai",
            missing_credentials=["AZURE_OPENAI_API_KEY"],
        )
        assert error.error_code == "PROVIDER_CREDENTIAL_ERROR"
        assert "AZURE_OPENAI_API_KEY" in error.message
        assert error.http_status_code == 422

    def test_ai_query_error(self) -> None:
        error = AIQueryError(message="Agent execution failed")
        assert error.error_code == "AI_QUERY_ERROR"
        assert error.http_status_code == 502


class TestConfigErrors:
    """Verify configuration domain error types."""

    def test_configuration_error(self) -> None:
        error = ConfigurationError(message="Missing APP_DB_URL")
        assert error.error_code == "CONFIGURATION_ERROR"
        assert error.http_status_code == 500


# --- Integration tests: exception handlers with real HTTP requests ---


@pytest.fixture
def app():
    """Create a fresh app for handler integration tests."""
    from fastapi import FastAPI

    from app.errors.handlers import register_exception_handlers, unhandled_exception_handler

    test_app = FastAPI()

    register_exception_handlers(test_app)

    @test_app.middleware("http")
    async def request_id_middleware(request, call_next):
        import uuid

        request.state.request_id = str(uuid.uuid4())
        try:
            response = await call_next(request)
        except Exception as exc:
            return await unhandled_exception_handler(request, exc)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @test_app.get("/raise-not-found")
    async def raise_not_found():
        raise ProjectNotFoundError(project_id="test-123")

    @test_app.get("/raise-validation")
    async def raise_validation():
        raise ProjectValidationError(message="Name too short", detail="min 3 chars")

    @test_app.get("/raise-connection")
    async def raise_connection():
        raise DataSourceConnectionError(
            source_type="postgresql",
            message="Connection refused",
        )

    @test_app.get("/raise-unhandled")
    async def raise_unhandled():
        raise RuntimeError("Internal database crash with secret path /var/db/creds")

    from pydantic import BaseModel

    class TestBody(BaseModel):
        name: str
        age: int

    @test_app.post("/validate")
    async def validate_body(body: TestBody):
        return {"ok": True}

    return test_app


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client for exception handler tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestExceptionHandlerIntegration:
    """Verify exception handlers produce correct HTTP responses."""

    @pytest.mark.asyncio
    async def test_domain_error_returns_correct_status(self, client) -> None:
        response = await client.get("/raise-not-found")
        assert response.status_code == 404
        body = response.json()
        assert body["error_code"] == "PROJECT_NOT_FOUND"
        assert "test-123" in body["message"]
        assert "request_id" in body

    @pytest.mark.asyncio
    async def test_domain_error_includes_detail(self, client) -> None:
        response = await client.get("/raise-validation")
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "PROJECT_VALIDATION_ERROR"
        assert body["detail"] == "min 3 chars"

    @pytest.mark.asyncio
    async def test_connection_error_returns_502(self, client) -> None:
        response = await client.get("/raise-connection")
        assert response.status_code == 502
        body = response.json()
        assert body["error_code"] == "DATA_SOURCE_CONNECTION_ERROR"

    @pytest.mark.asyncio
    async def test_unhandled_error_returns_500_without_internals(self, client) -> None:
        response = await client.get("/raise-unhandled")
        assert response.status_code == 500
        body = response.json()
        assert body["error_code"] == "INTERNAL_ERROR"
        assert body["message"] == "An unexpected error occurred"
        # Must NOT expose stack traces, file paths, or class names
        assert "RuntimeError" not in body["message"]
        assert "/var/db/creds" not in body["message"]
        assert "detail" not in body  # detail excluded for 500
        assert "request_id" in body

    @pytest.mark.asyncio
    async def test_validation_error_returns_field_errors(self, client) -> None:
        response = await client.post(
            "/validate",
            json={"name": 123},  # missing 'age', wrong type for implied constraint
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert body["message"] == "Request validation failed"
        assert "field_errors" in body
        assert len(body["field_errors"]) > 0
        assert "request_id" in body

    @pytest.mark.asyncio
    async def test_response_includes_request_id_header(self, client) -> None:
        response = await client.get("/raise-not-found")
        assert "x-request-id" in response.headers
        # Request ID in body matches header
        body = response.json()
        assert body["request_id"] == response.headers["x-request-id"]
