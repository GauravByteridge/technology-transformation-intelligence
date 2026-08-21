"""
Property-based test for Recent Files Ordering and Limiting (Property 2).

**Validates: Requirements 2.5**

For any list of uploaded files, the dashboard's recent files list SHALL be
sorted by upload date in descending order (most recent first) and limited
to at most 5 files.
"""

import pytest
from datetime import datetime, timedelta
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

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_property_recent_files_ordering.db"

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

# Base datetime for generating upload dates
BASE_DATE = datetime(2024, 1, 1)

# Strategy for generating a list of unique upload dates (as offset minutes from base)
# Using unique offsets ensures distinct upload times for reliable ordering
unique_date_offsets = st.lists(
    st.integers(min_value=0, max_value=525600),  # up to 1 year in minutes
    min_size=1,
    max_size=15,
    unique=True,
)

# File type options
file_types = st.sampled_from(["pdf", "xlsx", "xls", "csv", "json"])

# Category options
categories = st.sampled_from([
    "Project Costs",
    "Burndown",
    "Audit",
    "IT Controls",
    "Remediation",
    "Business Intelligence",
    "Internal Data",
    "Other",
])


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestRecentFilesOrderingProperty:
    """
    Property 2: Recent Files Ordering and Limiting

    **Validates: Requirements 2.5**

    For any list of uploaded files, the dashboard's recent files list SHALL be
    sorted by upload date in descending order (most recent first) and limited
    to at most 5 files.
    """

    @given(date_offsets=unique_date_offsets)
    @settings(max_examples=50, deadline=None)
    def test_recent_files_sorted_descending_and_limited_to_5(self, date_offsets):
        """
        Property: For any set of files with distinct upload dates, the
        dashboard returns at most 5 files sorted by upload date descending.
        """
        # Set up fresh database for each example
        Base.metadata.create_all(bind=engine)
        try:
            db = TestSessionLocal()
            try:
                # Create a project
                project = Project(name="Test Project", description="Test")
                db.add(project)
                db.commit()
                db.refresh(project)

                # Create files with the generated upload dates
                upload_dates = [
                    BASE_DATE + timedelta(minutes=offset) for offset in date_offsets
                ]
                for i, upload_date in enumerate(upload_dates):
                    file = File(
                        file_name=f"file_{i}.pdf",
                        file_type="pdf",
                        category="Other",
                        file_path=f"/uploads/file_{i}.pdf",
                        chunk_count=0,
                        uploaded_at=upload_date,
                        project_id=project.id,
                    )
                    db.add(file)
                db.commit()
            finally:
                db.close()

            # Query the dashboard endpoint
            client = TestClient(app)
            response = client.get("/api/dashboard")
            assert response.status_code == 200

            data = response.json()
            recent_files = data["recent_files"]

            # Property 1: Limited to at most 5 files
            assert len(recent_files) <= 5, (
                f"Expected at most 5 recent files, got {len(recent_files)}"
            )

            # Property 2: Number of recent files is min(total_uploaded, 5)
            expected_count = min(len(date_offsets), 5)
            assert len(recent_files) == expected_count, (
                f"Expected {expected_count} recent files for "
                f"{len(date_offsets)} uploaded, got {len(recent_files)}"
            )

            # Property 3: Files are sorted by upload date descending
            if len(recent_files) > 1:
                upload_dates_returned = [
                    datetime.fromisoformat(f["uploaded_at"]) for f in recent_files
                ]
                for i in range(len(upload_dates_returned) - 1):
                    assert upload_dates_returned[i] >= upload_dates_returned[i + 1], (
                        f"Files not in descending order at index {i}: "
                        f"{upload_dates_returned[i]} should be >= "
                        f"{upload_dates_returned[i + 1]}"
                    )

            # Property 4: The returned files are the 5 most recent ones
            sorted_dates_desc = sorted(upload_dates, reverse=True)
            expected_dates = sorted_dates_desc[:5]
            upload_dates_returned = [
                datetime.fromisoformat(f["uploaded_at"]).replace(tzinfo=None)
                for f in recent_files
            ]
            assert upload_dates_returned == expected_dates, (
                f"Returned files are not the most recent ones. "
                f"Expected: {expected_dates}, Got: {upload_dates_returned}"
            )
        finally:
            Base.metadata.drop_all(bind=engine)

    @given(
        date_offsets=st.lists(
            st.integers(min_value=0, max_value=525600),
            min_size=6,
            max_size=15,
            unique=True,
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_more_than_5_files_returns_exactly_5(self, date_offsets):
        """
        Property: When more than 5 files exist, the dashboard returns
        exactly 5 files (the most recent ones).
        """
        assume(len(date_offsets) > 5)

        Base.metadata.create_all(bind=engine)
        try:
            db = TestSessionLocal()
            try:
                project = Project(name="Test Project", description="Test")
                db.add(project)
                db.commit()
                db.refresh(project)

                upload_dates = [
                    BASE_DATE + timedelta(minutes=offset) for offset in date_offsets
                ]
                for i, upload_date in enumerate(upload_dates):
                    file = File(
                        file_name=f"file_{i}.csv",
                        file_type="csv",
                        category="Audit",
                        file_path=f"/uploads/file_{i}.csv",
                        chunk_count=i,
                        uploaded_at=upload_date,
                        project_id=project.id,
                    )
                    db.add(file)
                db.commit()
            finally:
                db.close()

            client = TestClient(app)
            response = client.get("/api/dashboard")
            assert response.status_code == 200

            data = response.json()
            recent_files = data["recent_files"]

            # Must be exactly 5
            assert len(recent_files) == 5, (
                f"Expected exactly 5 recent files when {len(date_offsets)} "
                f"files exist, got {len(recent_files)}"
            )
        finally:
            Base.metadata.drop_all(bind=engine)
