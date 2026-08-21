"""
Property-based test for Unsupported File Type Rejection (Property 3).

**Validates: Requirements 3.4**

For any file with a type NOT in the set {pdf, xlsx, xls, csv, json},
the system SHALL reject the upload attempt and return an error message
without storing the file.
"""

import io
import os

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base, get_db
from main import app
from models.database_models import File, Project


# ---------------------------------------------------------------------------
# Test database setup (SQLite in-memory)
# ---------------------------------------------------------------------------

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_property_unsupported_file_type.db"

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
# Supported file types (these should be ACCEPTED, so we exclude them)
# ---------------------------------------------------------------------------

SUPPORTED_FILE_TYPES = {"pdf", "xlsx", "xls", "csv", "json"}


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for generating unsupported file extensions
# Generate alphabetic strings that are NOT in the supported set
unsupported_extensions = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
    min_size=1,
    max_size=10,
).filter(lambda ext: ext.lower() not in SUPPORTED_FILE_TYPES)

# Strategy for generating valid base filenames (non-empty, no dots)
base_filenames = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
    min_size=1,
    max_size=30,
)

# Combined strategy: filename with unsupported extension
unsupported_filenames = st.builds(
    lambda base, ext: f"{base}.{ext}",
    base_filenames,
    unsupported_extensions,
)


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestUnsupportedFileTypeRejectionProperty:
    """
    Property 3: Unsupported File Type Rejection

    **Validates: Requirements 3.4**

    For any file with a type NOT in the set {pdf, xlsx, xls, csv, json},
    the system SHALL reject the upload attempt and return an error message
    without storing the file.
    """

    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Create tables before each test and drop them after."""
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)

    def _create_project(self):
        """Helper to create a project in the database (required for upload)."""
        db = TestSessionLocal()
        try:
            project = Project(name="Test Project", description="For testing")
            db.add(project)
            db.commit()
            db.refresh(project)
            return project.id
        finally:
            db.close()

    @given(filename=unsupported_filenames)
    @settings(max_examples=100)
    def test_unsupported_file_type_rejected_with_400(self, filename):
        """
        Property: For any file with an extension NOT in {pdf, xlsx, xls, csv, json},
        the API returns HTTP 400 with an error message.
        """
        Base.metadata.create_all(bind=engine)
        try:
            # Create a project so the upload endpoint doesn't 404
            self._create_project()

            client = TestClient(app)

            # Create a dummy file with the unsupported filename
            file_content = b"dummy content for testing"
            files = {"file": (filename, io.BytesIO(file_content), "application/octet-stream")}

            response = client.post(
                "/api/files/upload",
                files=files,
                params={"category": "Other"},
            )

            # Must be rejected with 400
            assert response.status_code == 400, (
                f"Expected 400 for filename={filename!r}, got {response.status_code}"
            )

            # Must include a detail field with an error message
            data = response.json()
            assert "detail" in data, (
                f"Response missing 'detail' field for filename={filename!r}"
            )
            assert isinstance(data["detail"], str) and len(data["detail"]) > 0, (
                f"'detail' must be a non-empty string for filename={filename!r}"
            )
        finally:
            Base.metadata.drop_all(bind=engine)

    @given(filename=unsupported_filenames)
    @settings(max_examples=100)
    def test_no_file_record_stored_for_unsupported_type(self, filename):
        """
        Property: For any file with an unsupported extension, no file record
        is created in the database after the rejected upload attempt.
        """
        Base.metadata.create_all(bind=engine)
        try:
            # Create a project so the upload endpoint doesn't 404
            self._create_project()

            client = TestClient(app)

            # Attempt upload with unsupported file type
            file_content = b"dummy content for testing"
            files = {"file": (filename, io.BytesIO(file_content), "application/octet-stream")}

            client.post(
                "/api/files/upload",
                files=files,
                params={"category": "Other"},
            )

            # Verify no file was stored in the database
            db = TestSessionLocal()
            try:
                file_count = db.query(File).count()
                assert file_count == 0, (
                    f"Expected 0 files after uploading unsupported filename={filename!r}, "
                    f"found {file_count}"
                )
            finally:
                db.close()
        finally:
            Base.metadata.drop_all(bind=engine)

    @given(filename=unsupported_filenames)
    @settings(max_examples=100)
    def test_no_file_stored_on_disk_for_unsupported_type(self, filename):
        """
        Property: For any file with an unsupported extension, the file content
        is not persisted to the uploads directory.
        """
        Base.metadata.create_all(bind=engine)
        try:
            # Create a project so the upload endpoint doesn't 404
            self._create_project()

            client = TestClient(app)

            # Get the upload directory path
            upload_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "uploads"
            )

            # Count existing files before the upload attempt
            files_before = set(os.listdir(upload_dir)) if os.path.exists(upload_dir) else set()

            # Attempt upload with unsupported file type
            file_content = b"dummy content for testing"
            files = {"file": (filename, io.BytesIO(file_content), "application/octet-stream")}

            client.post(
                "/api/files/upload",
                files=files,
                params={"category": "Other"},
            )

            # Verify no new file was stored on disk
            files_after = set(os.listdir(upload_dir)) if os.path.exists(upload_dir) else set()
            new_files = files_after - files_before
            assert len(new_files) == 0, (
                f"Expected no new files on disk after uploading unsupported "
                f"filename={filename!r}, but found new files: {new_files}"
            )
        finally:
            Base.metadata.drop_all(bind=engine)
