"""
Integration tests for DataSourceService source connection operations against SQLite.

Verifies: create (both existence checks), list, delete, duplicate handling.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.datasource_errors import (
    DataSourceNotFoundError,
    DuplicateSourceConnectionError,
)
from app.errors.project_errors import ProjectNotFoundError
from app.models.data_source import DataSource
from app.models.project import Project
from app.models.user import User
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.security.credential_encryptor import CredentialEncryptor
from app.services.data_source_service import DataSourceService

# Use a proper uuid4 to avoid Python 3.14 SQLite UUID storage edge case
TEST_SYSTEM_USER_ID = uuid4()


async def _setup(session: AsyncSession):
    """Create system user, a project, and a data source for tests."""
    user = User(id=TEST_SYSTEM_USER_ID, email="system@test.com", name="System", role="system")
    session.add(user)
    await session.flush()

    project = Project(name="SC Test Project", created_by=TEST_SYSTEM_USER_ID)
    session.add(project)
    await session.flush()
    await session.refresh(project)

    ds = DataSource(
        name="SC Test DS",
        source_type="postgresql",
        display_label="PG",
        connection_config={"host": "localhost"},
    )
    session.add(ds)
    await session.flush()
    await session.refresh(ds)

    fernet_key = Fernet.generate_key().decode()
    encryptor = CredentialEncryptor(fernet_key)
    service = DataSourceService(
        data_source_repository=DataSourceRepository(session),
        project_repository=ProjectRepository(session),
        source_connection_repository=SourceConnectionRepository(session),
        credential_encryptor=encryptor,
    )

    return service, project.id, ds.id


class TestSourceConnectionService:
    """Integration tests for source connection operations."""

    @pytest.mark.asyncio
    async def test_create_source_connection_succeeds(self, async_session: AsyncSession):
        service, project_id, data_source_id = await _setup(async_session)

        result = await service.create_source_connection(
            project_id=project_id,
            data_source_id=data_source_id,
            purpose="analytics",
        )

        assert result["project_id"] == project_id
        assert result["data_source_id"] == data_source_id
        assert result["purpose"] == "analytics"

    @pytest.mark.asyncio
    async def test_create_source_connection_raises_when_project_missing(self, async_session: AsyncSession):
        service, _, data_source_id = await _setup(async_session)

        with pytest.raises(ProjectNotFoundError):
            await service.create_source_connection(
                project_id=uuid4(),
                data_source_id=data_source_id,
                purpose="test",
            )

    @pytest.mark.asyncio
    async def test_create_source_connection_raises_when_data_source_missing(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with pytest.raises(DataSourceNotFoundError):
            await service.create_source_connection(
                project_id=project_id,
                data_source_id=uuid4(),
                purpose="test",
            )

    @pytest.mark.asyncio
    async def test_create_duplicate_source_connection_raises_error(self, async_session: AsyncSession):
        service, project_id, data_source_id = await _setup(async_session)

        await service.create_source_connection(
            project_id=project_id,
            data_source_id=data_source_id,
            purpose="first",
        )

        with pytest.raises(DuplicateSourceConnectionError):
            await service.create_source_connection(
                project_id=project_id,
                data_source_id=data_source_id,
                purpose="duplicate",
            )

    @pytest.mark.asyncio
    async def test_list_source_connections_returns_project_connections(self, async_session: AsyncSession):
        service, project_id, data_source_id = await _setup(async_session)

        await service.create_source_connection(
            project_id=project_id,
            data_source_id=data_source_id,
            purpose="analytics",
        )

        connections = await service.list_source_connections(project_id)

        assert len(connections) == 1
        assert connections[0]["data_source_id"] == data_source_id

    @pytest.mark.asyncio
    async def test_delete_source_connection_removes_connection(self, async_session: AsyncSession):
        service, project_id, data_source_id = await _setup(async_session)

        await service.create_source_connection(
            project_id=project_id,
            data_source_id=data_source_id,
            purpose="analytics",
        )

        await service.delete_source_connection(project_id, data_source_id)

        connections = await service.list_source_connections(project_id)
        assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_delete_source_connection_raises_when_not_found(self, async_session: AsyncSession):
        service, project_id, _ = await _setup(async_session)

        with pytest.raises(DataSourceNotFoundError):
            await service.delete_source_connection(project_id, uuid4())
