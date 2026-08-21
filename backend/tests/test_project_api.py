"""
Unit tests for the project API endpoints.

Tests POST /api/project, GET /api/project, and DELETE /api/project/reset
using an in-memory SQLite database to avoid PostgreSQL dependency.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base, get_db
from main import app
from models.database_models import Project


# ---------------------------------------------------------------------------
# Test database setup (SQLite in-memory)
# ---------------------------------------------------------------------------

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_project.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Provide a test database session."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/project tests
# ---------------------------------------------------------------------------


class TestCreateProject:
    """Tests for POST /api/project endpoint."""

    def test_create_project_success(self, client):
        """Creating a project with a valid name returns 201."""
        response = client.post(
            "/api/project",
            json={"name": "Test Project", "description": "A test project"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"
        assert "id" in data
        assert "created_at" in data

    def test_create_project_without_description(self, client):
        """Creating a project without a description succeeds."""
        response = client.post("/api/project", json={"name": "My Project"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Project"
        assert data["description"] is None

    def test_create_project_empty_name_returns_400(self, client):
        """Empty project name returns 400 error."""
        response = client.post("/api/project", json={"name": ""})
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "empty" in data["detail"].lower() or "whitespace" in data["detail"].lower()

    def test_create_project_whitespace_name_returns_400(self, client):
        """Whitespace-only project name returns 400 error."""
        response = client.post("/api/project", json={"name": "   "})
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_create_project_already_exists_returns_409(self, client):
        """Creating a project when one already exists returns 409."""
        # Create first project
        client.post("/api/project", json={"name": "First Project"})

        # Try to create another
        response = client.post("/api/project", json={"name": "Second Project"})
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()

    def test_create_project_strips_name(self, client):
        """Project name is trimmed of leading/trailing whitespace."""
        response = client.post("/api/project", json={"name": "  Trimmed Name  "})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Trimmed Name"


# ---------------------------------------------------------------------------
# GET /api/project tests
# ---------------------------------------------------------------------------


class TestGetProject:
    """Tests for GET /api/project endpoint."""

    def test_get_project_when_exists(self, client):
        """GET returns project data when a project exists."""
        # Create a project first
        client.post(
            "/api/project",
            json={"name": "My Project", "description": "Description"},
        )

        response = client.get("/api/project")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Project"
        assert data["description"] == "Description"
        assert "id" in data
        assert "created_at" in data

    def test_get_project_when_none_exists_returns_404(self, client):
        """GET returns 404 when no project exists."""
        response = client.get("/api/project")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "no project" in data["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE /api/project/reset tests
# ---------------------------------------------------------------------------


class TestResetProject:
    """Tests for DELETE /api/project/reset endpoint."""

    @patch("api.project.delete_all_embeddings")
    def test_reset_project_success(self, mock_delete_embeddings, client):
        """Reset deletes project and returns success message."""
        # Create a project first
        client.post("/api/project", json={"name": "My Project"})

        response = client.delete("/api/project/reset")
        assert response.status_code == 200
        data = response.json()
        assert "detail" in data
        assert "reset" in data["detail"].lower()

        # Verify project no longer exists
        get_response = client.get("/api/project")
        assert get_response.status_code == 404

        # Verify ChromaDB was called to delete embeddings
        mock_delete_embeddings.assert_called_once()

    def test_reset_when_no_project_returns_404(self, client):
        """Reset returns 404 when no project exists."""
        response = client.delete("/api/project/reset")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
