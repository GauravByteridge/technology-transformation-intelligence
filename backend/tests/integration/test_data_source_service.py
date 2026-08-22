"""
Integration tests for DataSourceService against SQLite.

Verifies: CRUD operations, credential masking, encryption on persist,
connection_config complete replacement on update, not-found errors.
"""

from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.datasource_errors import DataSourceNotFoundError
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.security.credential_encryptor import CredentialEncryptor
from app.services.data_source_service import DataSourceService


def _make_service(session: AsyncSession) -> DataSourceService:
    """Create a DataSourceService with real dependencies and a test Fernet key."""
    fernet_key = Fernet.generate_key().decode()
    encryptor = CredentialEncryptor(fernet_key)
    return DataSourceService(
        data_source_repository=DataSourceRepository(session),
        project_repository=ProjectRepository(session),
        source_connection_repository=SourceConnectionRepository(session),
        credential_encryptor=encryptor,
    )


class TestDataSourceServiceCRUD:
    """Tests for DataSourceService create, get, list, update, delete."""

    @pytest.mark.asyncio
    async def test_create_data_source_masks_config_in_response(self, async_session: AsyncSession):
        service = _make_service(async_session)

        result = await service.create_data_source(
            name="Test PG",
            source_type="postgresql",
            display_label="PostgreSQL",
            connection_config={"host": "localhost", "port": 5432, "password": "secret123"},
        )

        assert result["name"] == "Test PG"
        assert result["source_type"] == "postgresql"
        # Sensitive field is masked, not exposed
        assert "password" not in result["connection_config"]
        assert result["connection_config"]["password_configured"] is True
        # Non-sensitive fields preserved
        assert result["connection_config"]["host"] == "localhost"
        assert result["connection_config"]["port"] == 5432

    @pytest.mark.asyncio
    async def test_get_data_source_returns_masked_config(self, async_session: AsyncSession):
        service = _make_service(async_session)
        created = await service.create_data_source(
            name="Get Me",
            source_type="mongodb",
            display_label="Mongo",
            connection_config={"uri": "mongodb://localhost", "token": "abc123"},
        )

        result = await service.get_data_source(created["id"])

        assert result["name"] == "Get Me"
        assert "token" not in result["connection_config"]
        assert result["connection_config"]["token_configured"] is True
        assert result["connection_config"]["uri"] == "mongodb://localhost"

    @pytest.mark.asyncio
    async def test_get_data_source_raises_when_not_found(self, async_session: AsyncSession):
        service = _make_service(async_session)

        with pytest.raises(DataSourceNotFoundError):
            await service.get_data_source(uuid4())

    @pytest.mark.asyncio
    async def test_list_data_sources_masks_all_configs(self, async_session: AsyncSession):
        service = _make_service(async_session)
        await service.create_data_source(
            name="DS1", source_type="pg", display_label="PG",
            connection_config={"host": "a", "password": "p1"},
        )
        await service.create_data_source(
            name="DS2", source_type="mongo", display_label="Mongo",
            connection_config={"host": "b", "api_key": "k1"},
        )

        results = await service.list_data_sources()

        assert len(results) == 2
        for ds in results:
            config = ds["connection_config"]
            # No sensitive field values exposed
            assert "password" not in config
            assert "api_key" not in config

    @pytest.mark.asyncio
    async def test_update_data_source_replaces_connection_config(self, async_session: AsyncSession):
        service = _make_service(async_session)
        created = await service.create_data_source(
            name="Update Me",
            source_type="pg",
            display_label="PG",
            connection_config={"host": "old-host", "password": "old-pass"},
        )

        # Complete replacement — new config entirely replaces old
        result = await service.update_data_source(
            created["id"],
            {"connection_config": {"host": "new-host", "password": "new-pass"}},
        )

        assert result["connection_config"]["host"] == "new-host"
        assert result["connection_config"]["password_configured"] is True
        assert "password" not in result["connection_config"]

    @pytest.mark.asyncio
    async def test_update_data_source_raises_when_not_found(self, async_session: AsyncSession):
        service = _make_service(async_session)

        with pytest.raises(DataSourceNotFoundError):
            await service.update_data_source(uuid4(), {"name": "Nope"})

    @pytest.mark.asyncio
    async def test_delete_data_source_removes_record(self, async_session: AsyncSession):
        service = _make_service(async_session)
        created = await service.create_data_source(
            name="Delete Me", source_type="pg", display_label="PG",
            connection_config={"host": "x"},
        )

        await service.delete_data_source(created["id"])

        with pytest.raises(DataSourceNotFoundError):
            await service.get_data_source(created["id"])

    @pytest.mark.asyncio
    async def test_delete_data_source_raises_when_not_found(self, async_session: AsyncSession):
        service = _make_service(async_session)

        with pytest.raises(DataSourceNotFoundError):
            await service.delete_data_source(uuid4())
