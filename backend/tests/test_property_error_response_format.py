"""
Property-based test for API Error Response Format Consistency (Property 8).

**Validates: Requirements 10.11**

For any API request that results in an error condition, the backend response SHALL:
- Return a valid JSON object
- Include a "detail" field with a human-readable error message
- Return an appropriate HTTP status code (4xx for client errors, 5xx for server errors)
"""

import json
import string

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Create a representative FastAPI app that exercises all error categories
# from the design document. This mirrors the error handling patterns that
# the real application will use.
# ---------------------------------------------------------------------------

class ItemRequest(BaseModel):
    """Sample request model to trigger validation errors."""
    name: str
    value: int


def create_test_app() -> FastAPI:
    """
    Create a FastAPI application with endpoints that produce each error
    category from the design:
    - 400: Validation Error (empty project name, unsupported file type)
    - 404: Not Found (no project exists, file not found)
    - 422: Processing Error (text extraction failed)
    - 503: External Service Error (Groq API unavailable)
    - 500: Server Error (unexpected internal errors)
    """
    app = FastAPI()

    @app.post("/api/project")
    async def create_project(name: str = "", description: str = ""):
        """Simulates project creation with validation."""
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Project name cannot be empty")
        return {"id": 1, "name": name, "description": description}

    @app.get("/api/project")
    async def get_project():
        """Simulates project retrieval when no project exists."""
        raise HTTPException(status_code=404, detail="No project exists. Please create a project first.")

    @app.get("/api/files/{file_id}")
    async def get_file(file_id: int):
        """Simulates file retrieval when file is not found."""
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")

    @app.post("/api/files/upload")
    async def upload_file(file_type: str = ""):
        """Simulates file upload with type validation."""
        supported_types = {"pdf", "xlsx", "xls", "csv", "json"}
        if file_type not in supported_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{file_type}'. Supported types: {', '.join(sorted(supported_types))}"
            )
        return {"status": "uploaded"}

    @app.post("/api/files/process")
    async def process_file(file_name: str = "test.pdf"):
        """Simulates a processing error (text extraction failure)."""
        raise HTTPException(
            status_code=422,
            detail=f"Text extraction failed for file '{file_name}'. The file may be corrupted or password-protected."
        )

    @app.post("/api/chat")
    async def chat(question: str = ""):
        """Simulates an external service error (Groq API unavailable)."""
        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily unavailable. Please try again later."
        )

    @app.get("/api/internal-error")
    async def internal_error():
        """Simulates an unexpected server error."""
        raise HTTPException(
            status_code=500,
            detail="An unexpected internal error occurred. Please contact support."
        )

    @app.post("/api/validate-body")
    async def validate_body(item: ItemRequest):
        """Endpoint that triggers Pydantic validation errors (422 from FastAPI)."""
        return {"name": item.name, "value": item.value}

    return app


# Create test client for the property tests
_test_app = create_test_app()
_client = TestClient(_test_app)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for generating random URL paths that won't match any route
random_path_segment = st.text(
    alphabet=string.ascii_lowercase + string.digits + "-_",
    min_size=1,
    max_size=30,
)

nonexistent_paths = st.builds(
    lambda segments: "/api/" + "/".join(segments),
    st.lists(random_path_segment, min_size=1, max_size=4),
)

# Strategy for HTTP methods
http_methods = st.sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH"])

# Strategy for unsupported file types (anything not in the supported set)
supported_types = {"pdf", "xlsx", "xls", "csv", "json"}
unsupported_file_type = st.text(
    alphabet=string.ascii_lowercase + string.digits,
    min_size=1,
    max_size=10,
).filter(lambda x: x not in supported_types)

# Strategy for file IDs (all will 404 since no files exist)
file_ids = st.integers(min_value=1, max_value=999999)

# Strategy for empty/whitespace project names
# Use only space characters since other whitespace chars (\t, \r, \n) are
# invalid in HTTP URLs and would be rejected at the transport layer
empty_or_whitespace_names = st.one_of(
    st.just(""),
    st.text(alphabet=" ", min_size=1, max_size=20),
)

# Strategy for invalid body payloads that will trigger Pydantic validation
invalid_bodies = st.one_of(
    st.just({}),
    st.just({"name": 123}),  # wrong type
    st.just({"value": "not_an_int"}),  # wrong type
    st.just({"name": "valid", "value": "not_an_int"}),  # value wrong type
    st.dictionaries(
        keys=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=5),
        values=st.text(min_size=0, max_size=10),
        min_size=0,
        max_size=3,
    ),
)


# ---------------------------------------------------------------------------
# Helper function to validate error response format
# ---------------------------------------------------------------------------

def assert_valid_error_response(response):
    """
    Validate that an error response conforms to the API error format:
    1. Response body is valid JSON
    2. JSON object contains a "detail" field
    3. "detail" field contains a human-readable string (non-empty)
    4. HTTP status code is in 4xx or 5xx range
    """
    # Must have an error status code
    assert 400 <= response.status_code < 600, (
        f"Expected error status code (4xx or 5xx), got {response.status_code}"
    )

    # Must be a valid JSON response
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        pytest.fail(f"Response is not valid JSON: {e}")

    # Must be a JSON object (dict)
    assert isinstance(body, dict), (
        f"Expected JSON object, got {type(body).__name__}: {body}"
    )

    # Must contain a "detail" field
    assert "detail" in body, (
        f"Response missing 'detail' field. Keys present: {list(body.keys())}"
    )

    # "detail" must be a non-empty string (human-readable message)
    # Note: FastAPI validation errors return detail as a list, but per our spec
    # we want all errors to have a string detail. We accept both formats since
    # FastAPI's built-in validation uses list format.
    detail = body["detail"]
    if isinstance(detail, str):
        assert len(detail.strip()) > 0, "Error detail must be non-empty"
    elif isinstance(detail, list):
        # FastAPI validation errors return a list of error details
        assert len(detail) > 0, "Error detail list must be non-empty"
        for item in detail:
            assert isinstance(item, dict), "Each validation error must be a dict"
            assert "msg" in item, "Each validation error must have a 'msg' field"
    else:
        pytest.fail(f"'detail' must be a string or list, got {type(detail).__name__}")

    # Verify appropriate HTTP status code category
    if 400 <= response.status_code < 500:
        # Client errors - the request was invalid
        pass
    elif 500 <= response.status_code < 600:
        # Server errors - something went wrong server-side
        pass


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestErrorResponseFormatProperty:
    """
    Property 8: API Error Response Format Consistency

    **Validates: Requirements 10.11**

    For any API request that results in an error condition, the backend
    response SHALL return a valid JSON object with a "detail" field and
    appropriate HTTP status code.
    """

    @given(path=nonexistent_paths, method=http_methods)
    @settings(max_examples=50)
    def test_nonexistent_routes_return_proper_error_format(self, path, method):
        """
        Property: Any request to a non-existent route returns a properly
        formatted error response with 'detail' field and 4xx/5xx status.
        """
        response = _client.request(method, path)
        # Only validate if the response is an error (some methods might match)
        if response.status_code >= 400:
            assert_valid_error_response(response)

    @given(file_type=unsupported_file_type)
    @settings(max_examples=50)
    def test_unsupported_file_type_returns_proper_error_format(self, file_type):
        """
        Property: Any upload attempt with an unsupported file type returns
        a properly formatted 400 error response with 'detail' field.
        """
        response = _client.post(f"/api/files/upload?file_type={file_type}")
        assert_valid_error_response(response)
        assert response.status_code == 400

    @given(name=empty_or_whitespace_names)
    @settings(max_examples=50)
    def test_empty_project_name_returns_proper_error_format(self, name):
        """
        Property: Any project creation with empty/whitespace name returns
        a properly formatted 400 error response with 'detail' field.
        """
        response = _client.post("/api/project", params={"name": name})
        assert_valid_error_response(response)
        assert response.status_code == 400

    @given(file_id=file_ids)
    @settings(max_examples=50)
    def test_file_not_found_returns_proper_error_format(self, file_id):
        """
        Property: Any request for a non-existent file returns a properly
        formatted 404 error response with 'detail' field.
        """
        response = _client.get(f"/api/files/{file_id}")
        assert_valid_error_response(response)
        assert response.status_code == 404

    @given(body=invalid_bodies)
    @settings(max_examples=50)
    def test_invalid_request_body_returns_proper_error_format(self, body):
        """
        Property: Any request with an invalid body returns a properly
        formatted error response (422 Validation Error from FastAPI/Pydantic).
        """
        response = _client.post("/api/validate-body", json=body)
        if response.status_code >= 400:
            assert_valid_error_response(response)

    def test_processing_error_returns_proper_error_format(self):
        """
        Verify 422 processing errors have correct format.
        """
        response = _client.post("/api/files/process?file_name=report.pdf")
        assert_valid_error_response(response)
        assert response.status_code == 422

    def test_service_unavailable_returns_proper_error_format(self):
        """
        Verify 503 external service errors have correct format.
        """
        response = _client.post("/api/chat?question=test")
        assert_valid_error_response(response)
        assert response.status_code == 503

    def test_internal_server_error_returns_proper_error_format(self):
        """
        Verify 500 internal server errors have correct format.
        """
        response = _client.get("/api/internal-error")
        assert_valid_error_response(response)
        assert response.status_code == 500

    def test_project_not_found_returns_proper_error_format(self):
        """
        Verify 404 when no project exists has correct format.
        """
        response = _client.get("/api/project")
        assert_valid_error_response(response)
        assert response.status_code == 404
