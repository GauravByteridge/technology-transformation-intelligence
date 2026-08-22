"""
Integration tests for ProjectService against SQLite.

Verifies: CRUD operations, SYSTEM_USER_ID assignment, project existence checks.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import SYSTEM_USER_ID
from app.errors.project_errors import ProjectNotFoundError
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.projects import ProjectCreate
from app.services.project_service import ProjectService

# Use a proper uuid4 to avoid Python 3.14 SQLite UUID storage edge case
TEST_SYSTEM_USER_ID = uuid4()


async def _create_system_user(session: AsyncSession) -> User:
    """Create the system user to satisfy FK constraints."""
    user = User(id=TEST_SYSTEM_USER_ID, email="system@test.com", name="System", role="system")
    session.add(user)
    await session.flush()
    return user


class TestProjectService:
    """Integration tests for ProjectService full CRUD."""

    @pytest.mark.asyncio
    async def test_create_project_assigns_system_user_id(self, async_session: AsyncSession):
        await _create_system_user(async_session)
        with patch("app.services.project_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            service = ProjectService(ProjectRepository(async_session))

            result = await service.create_project(
                ProjectCreate(name="Test Project", description="A test")
            )

            assert result.name == "Test Project"
            assert result.description == "A test"
            assert result.status == "active"
            assert result.created_by == TEST_SYSTEM_USER_ID

    @pytest.mark.asyncio
    async def test_get_project_returns_project(self, async_session: AsyncSession):
        await _create_system_user(async_session)
        with patch("app.services.project_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            service = ProjectService(ProjectRepository(async_session))
            created = await service.create_project(ProjectCreate(name="Get Me"))

            result = await service.get_project(created.id)

            assert result.id == created.id
            assert result.name == "Get Me"

    @pytest.mark.asyncio
    async def test_get_project_raises_when_not_found(self, async_session: AsyncSession):
        service = ProjectService(ProjectRepository(async_session))

        with pytest.raises(ProjectNotFoundError):
            await service.get_project(uuid4())

    @pytest.mark.asyncio
    async def test_list_projects_returns_items_and_total(self, async_session: AsyncSession):
        await _create_system_user(async_session)
        with patch("app.services.project_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            service = ProjectService(ProjectRepository(async_session))
            await service.create_project(ProjectCreate(name="P1"))
            await service.create_project(ProjectCreate(name="P2"))

            result = await service.list_projects()

            assert result.total == 2
            assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_update_project_applies_changes(self, async_session: AsyncSession):
        await _create_system_user(async_session)
        with patch("app.services.project_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            service = ProjectService(ProjectRepository(async_session))
            created = await service.create_project(ProjectCreate(name="Original"))

            updated = await service.update_project(created.id, {"name": "Updated"})

            assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_update_project_raises_when_not_found(self, async_session: AsyncSession):
        service = ProjectService(ProjectRepository(async_session))

        with pytest.raises(ProjectNotFoundError):
            await service.update_project(uuid4(), {"name": "Nope"})

    @pytest.mark.asyncio
    async def test_delete_project_removes_project(self, async_session: AsyncSession):
        await _create_system_user(async_session)
        with patch("app.services.project_service.SYSTEM_USER_ID", TEST_SYSTEM_USER_ID):
            service = ProjectService(ProjectRepository(async_session))
            created = await service.create_project(ProjectCreate(name="Delete Me"))

            await service.delete_project(created.id)

            with pytest.raises(ProjectNotFoundError):
                await service.get_project(created.id)

    @pytest.mark.asyncio
    async def test_delete_project_raises_when_not_found(self, async_session: AsyncSession):
        service = ProjectService(ProjectRepository(async_session))

        with pytest.raises(ProjectNotFoundError):
            await service.delete_project(uuid4())
