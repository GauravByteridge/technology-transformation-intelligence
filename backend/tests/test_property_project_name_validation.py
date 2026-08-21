"""
Property-based test for Empty/Whitespace Project Name Rejection (Property 1).

**Validates: Requirements 1.4**

For any string that is empty or consists entirely of whitespace characters,
when submitted as a project name, the system SHALL reject the submission and
display a validation error without creating a project record.
"""

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base, get_db
from main import app
from models.database_models import Project


# ---------------------------------------------------------------------------
# Test database setup (SQLite in-memory)
# ---------------------------------------------------------------------------

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_property_project_name.db"

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


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for generating whitespace-only strings using common whitespace chars
whitespace_chars = " \t\n\r\x0b\x0c"

whitespace_only_names = st.text(
    alphabet=whitespace_chars,
    min_size=1,
    max_size=50,
)

# Strategy combining empty string and whitespace-only strings
empty_or_whitespace_names = st.one_of(
    st.just(""),
    whitespace_only_names,
)


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestProjectNameValidationProperty:
    """
    Property 1: Empty/Whitespace Project Name Rejection

    **Validates: Requirements 1.4**

    For any string that is empty or consists entirely of whitespace characters,
    when submitted as a project name, the system SHALL reject the submission
    and display a validation error without creating a project record.
    """

    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Create tables before each test and drop them after."""
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)

    @pytest.fixture
    def client(self):
        """Test client for the FastAPI app."""
        return TestClient(app)

    @given(name=empty_or_whitespace_names)
    @settings(max_examples=100)
    def test_empty_or_whitespace_name_rejected_with_400(self, name):
        """
        Property: For any empty or whitespace-only string submitted as a
        project name, the API returns HTTP 400 with a validation error.
        """
        # Recreate tables for each hypothesis example to ensure clean state
        Base.metadata.create_all(bind=engine)
        try:
            client = TestClient(app)
            response = client.post("/api/project", json={"name": name})

            # Must be rejected with 400
            assert response.status_code == 400, (
                f"Expected 400 for name={name!r}, got {response.status_code}"
            )

            # Must include a detail field with an error message
            data = response.json()
            assert "detail" in data, (
                f"Response missing 'detail' field for name={name!r}"
            )
            assert isinstance(data["detail"], str) and len(data["detail"]) > 0, (
                f"'detail' must be a non-empty string for name={name!r}"
            )
        finally:
            Base.metadata.drop_all(bind=engine)

    @given(name=empty_or_whitespace_names)
    @settings(max_examples=100)
    def test_no_project_record_created_for_invalid_name(self, name):
        """
        Property: For any empty or whitespace-only string submitted as a
        project name, no project record is created in the database.
        """
        Base.metadata.create_all(bind=engine)
        try:
            client = TestClient(app)
            # Attempt to create a project with invalid name
            client.post("/api/project", json={"name": name})

            # Verify no project was stored
            db = TestSessionLocal()
            try:
                project_count = db.query(Project).count()
                assert project_count == 0, (
                    f"Expected 0 projects after submitting name={name!r}, "
                    f"found {project_count}"
                )
            finally:
                db.close()
        finally:
            Base.metadata.drop_all(bind=engine)
