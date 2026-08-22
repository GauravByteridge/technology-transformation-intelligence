"""
Base repository module establishing secure database access patterns.

All repositories in this application MUST inherit from BaseRepository and use
SQLAlchemy's parameterized query mechanisms. This ensures SQL injection prevention
across the entire data access layer.

SECURITY INVARIANTS:
- All queries MUST use SQLAlchemy bound parameters (`:param_name` or `$1` style)
- String interpolation or f-strings for query construction are FORBIDDEN
- User-supplied input MUST NEVER be concatenated into SQL strings
- All database operations go through AsyncSession — no raw connection usage

WARNING: Never construct queries using string formatting with user input.
    Bad:  text(f"SELECT * FROM users WHERE id = '{user_id}'")
    Good: text("SELECT * FROM users WHERE id = :user_id").bindparams(user_id=user_id)
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Result, Select, delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository providing secure, parameterized database access patterns.

    All database queries in this application flow through repositories that
    inherit from this base class. This enforces:

    1. Parameterized queries only — SQLAlchemy bound parameters prevent SQL injection
    2. Async session management — consistent transaction handling
    3. Type-safe result mapping — explicit model types for all operations
    4. Read/write separation awareness — external sources are read-only

    Usage:
        class ProjectRepository(BaseRepository[Project]):
            def __init__(self, session: AsyncSession) -> None:
                super().__init__(session, Project)

            async def get_by_id(self, project_id: UUID) -> Project | None:
                return await self._get_by_id(project_id)
    """

    def __init__(self, session: AsyncSession, model_class: type[T]) -> None:
        """
        Initialize repository with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
                     Never instantiate sessions inside repository methods.
            model_class: The SQLAlchemy model class this repository manages.
        """
        self._session = session
        self._model_class = model_class

    async def _get_by_id(self, entity_id: UUID) -> T | None:
        """
        Retrieve a single entity by its primary key.

        Uses SQLAlchemy's parameterized query — the entity_id is bound
        as a parameter, never interpolated into the query string.

        Args:
            entity_id: UUID primary key of the entity.

        Returns:
            The entity instance or None if not found.
        """
        # NOTE: SQLAlchemy ORM .get() uses parameterized queries internally
        result = await self._session.get(self._model_class, entity_id)
        return result

    async def _list_all(self) -> list[T]:
        """
        Retrieve all entities of this repository's type.

        Returns:
            List of all entity instances.
        """
        statement: Select[tuple[T]] = select(self._model_class)
        result: Result[tuple[T]] = await self._session.execute(statement)
        return list(result.scalars().all())

    async def _create(self, entity: T) -> T:
        """
        Persist a new entity to the database.

        Args:
            entity: The model instance to persist.

        Returns:
            The persisted entity with generated fields populated.
        """
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def _delete_by_id(self, entity_id: UUID) -> bool:
        """
        Delete an entity by its primary key.

        Uses parameterized deletion — the entity_id is bound as a parameter.

        Args:
            entity_id: UUID primary key of the entity to delete.

        Returns:
            True if an entity was deleted, False if not found.
        """
        statement = delete(self._model_class).where(
            self._model_class.id == entity_id  # type: ignore[attr-defined]
        )
        result = await self._session.execute(statement)
        return result.rowcount > 0  # type: ignore[union-attr]

    async def _execute_parameterized(
        self, query: str, parameters: dict[str, Any]
    ) -> Result[Any]:
        """
        Execute a raw SQL query with explicit parameterized bindings.

        This method exists for cases where ORM queries are insufficient and
        raw SQL is required (e.g., complex joins, aggregations). It enforces
        that ALL parameters are bound — never interpolated.

        Args:
            query: SQL query string using :param_name placeholders.
                   Example: "SELECT * FROM projects WHERE status = :status"
            parameters: Dictionary mapping parameter names to values.
                   Example: {"status": "active"}

        Returns:
            SQLAlchemy Result object containing query results.

        WARNING: The `query` string MUST use named placeholders (:param_name).
                 NEVER construct query strings using f-strings, .format(), or
                 string concatenation with user-supplied values.

        Example:
            # CORRECT — parameterized
            result = await self._execute_parameterized(
                "SELECT * FROM projects WHERE name = :name AND status = :status",
                {"name": project_name, "status": "active"}
            )

            # WRONG — SQL injection vulnerability
            # result = await self._session.execute(
            #     text(f"SELECT * FROM projects WHERE name = '{project_name}'")
            # )
        """
        statement = text(query).bindparams(**parameters)
        return await self._session.execute(statement)
