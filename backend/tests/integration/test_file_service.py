"""
Integration tests for FileService against SQLite.

Verifies: create (project + optional data_source existence checks),
list, update status, delete, SYSTEM_USER_ID assignment, not-found errors.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.datasource_errors import DataSourceNotFoundError
from app.errors.file_errors import FileNotFoundError as DomainFileNotFoundError
from app.errors.project_errors import ProjectNotFoundError
from app.models.data_source import DataSource
from app.models.project import Project
from app.models.user import User
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import ProjectRepository
from app.services.file_service import FileService

# Use a proper uuid4 to avoid Python 3.14 SQLite UUID storage edge case
TEST_SYSTEM_USER_ID = uuid4()


async def _setup(session: AsyncSession, create_data_source: bool = False):
    """Create system user, project, and optionally a data source."""
    user = User(id=TEST_SYSTEM_USER_ID, email="system@test.com", name="System", role="system")
    session.add(user)
    await session.flush()

    project = Project(name="File Project", created_by=TEST_SYSTEM_USER_ID)
    session.add(project)
    await session.flush()
    await session.refresh(project)

    file_service = FileService(
        file_repository=FileRepository(session),
        project_repository=ProjectRepository(session),
        data_source_repository=DataSourceRepository(session),
    )

    data_source_id = None
    if create_data_source:
        ds = DataSource(
            name="File DS",
            source_type="pg",
            display_label="PG",
            connection_config={"host": "localhost"},
        )
        session.add(ds)
        await session.flush()
        await session.refresh(ds)
        data_source_id = ds.id

    return file_service, project.id, data_source_id


class TestFileService:
    """Integration tests for FileService."""

    @pytest.mark.asyncio
    async def test_create_file_assigns_system_user_id(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with patch("app.services.file_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            result = await service.create_file(
                project_id=project_id,
                file_name="report.pdf",
                file_type="pdf",
                file_size=1024,
            )

        assert result["file_name"] == "report.pdf"
        assert result["uploaded_by"] == TEST_SYSTEM_USER_ID
        assert result["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_create_file_with_data_source_verifies_existence(self, async_session: AsyncSession):
        service, project_id, data_source_id = await _setup(async_session, create_data_source=True)

        with patch("app.services.file_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            result = await service.create_file(
                project_id=project_id,
                file_name="data.csv",
                file_type="csv",
                file_size=512,
                data_source_id=data_source_id,
            )

        assert result["data_source_id"] == data_source_id

    @pytest.mark.asyncio
    async def test_create_file_raises_when_project_missing(self, async_session: AsyncSession):
        service, _, _ = await _setup(async_session)

        with patch("app.services.file_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            with pytest.raises(ProjectNotFoundError):
                await service.create_file(
                    project_id=uuid4(),
                    file_name="orphan.pdf",
                    file_type="pdf",
                    file_size=100,
                )

    @pytest.mark.asyncio
    async def test_create_file_raises_when_data_source_missing(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with patch("app.services.file_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            with pytest.raises(DataSourceNotFoundError):
                await service.create_file(
                    project_id=project_id,
                    file_name="orphan.csv",
                    file_type="csv",
                    file_size=100,
                    data_source_id=uuid4(),
                )

    @pytest.mark.asyncio
    async def test_get_file_returns_record(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with patch("app.services.file_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            created = await service.create_file(
                project_id=project_id, file_name="get_me.txt", file_type="txt", file_size=50,
            )

            result = await service.get_file(created["id"])

        assert result["id"] == created["id"]
        assert result["file_name"] == "get_me.txt"

    @pytest.mark.asyncio
    async def test_get_file_raises_when_not_found(self, async_session: AsyncSession):
        service, _, _ = await _setup(async_session)

        with pytest.raises(DomainFileNotFoundError):
            await service.get_file(uuid4())

    @pytest.mark.asyncio
    async def test_list_by_project_returns_files(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with patch("app.services.file_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            await service.create_file(
                project_id=project_id, file_name="a.csv", file_type="csv", file_size=100,
            )
            await service.create_file(
                project_id=project_id, file_name="b.xlsx", file_type="xlsx", file_size=200,
            )

            results = await service.list_by_project(project_id)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_update_file_applies_changes(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with patch("app.services.file_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            created = await service.create_file(
                project_id=project_id, file_name="update_me.pdf", file_type="pdf", file_size=300,
            )

            result = await service.update_file(created["id"], {"processing_status": "completed"})

        assert result["processing_status"] == "completed"

    @pytest.mark.asyncio
    async def test_update_file_raises_when_not_found(self, async_session: AsyncSession):
        service, _, _ = await _setup(async_session)

        with pytest.raises(DomainFileNotFoundError):
            await service.update_file(uuid4(), {"processing_status": "failed"})

    @pytest.mark.asyncio
    async def test_delete_file_removes_record(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with patch("app.services.file_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            created = await service.create_file(
                project_id=project_id, file_name="delete_me.txt", file_type="txt", file_size=10,
            )

            await service.delete_file(created["id"])

            with pytest.raises(DomainFileNotFoundError):
                await service.get_file(created["id"])

    @pytest.mark.asyncio
    async def test_delete_file_raises_when_not_found(self, async_session: AsyncSession):
        service, _, _ = await _setup(async_session)

        with pytest.raises(DomainFileNotFoundError):
            await service.delete_file(uuid4())
