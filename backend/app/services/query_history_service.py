"""
QueryHistory service — business logic layer for query history and saved query operations.

Manages append-only query history records and user-saved queries.
Query history records are never updated or deleted to maintain audit trail integrity.
"""

import structlog
from uuid import UUID

from app.constants import SYSTEM_USER_ID
from app.errors.project_errors import ProjectNotFoundError
from app.errors.query_errors import QueryHistoryNotFoundError, SavedQueryNotFoundError
from app.models.query import QueryHistory, SavedQuery
from app.repositories.project_repository import ProjectRepository
from app.repositories.query_history_repository import QueryHistoryRepository

logger = structlog.get_logger(__name__)


class QueryHistoryService:
    """
    Business logic for query history and saved query operations.

    Query history is append-only — no update or delete operations exist.
    This preserves a complete audit trail for AI query executions.
    """

    def __init__(
        self,
        query_history_repository: QueryHistoryRepository,
        project_repository: ProjectRepository,
    ) -> None:
        """
        Initialize with required dependencies.

        Args:
            query_history_repository: Repository for query history persistence.
            project_repository: Repository for project existence checks.
        """
        self._query_history_repo = query_history_repository
        self._project_repo = project_repository

    # --- Query History (append-only) ---

    async def create_query_history(
        self,
        project_id: UUID,
        conversation_id: UUID,
        query_id: UUID,
        question: str,
        response: dict | None = None,
        tools_invoked: list | None = None,
        sources_consulted: list | None = None,
        is_partial: bool = False,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        prompt_version: str | None = None,
        duration_ms: int | None = None,
    ) -> dict:
        """
        Create a new query history record.

        Verifies project exists before creating.

        Args:
            project_id: UUID of the project.
            conversation_id: UUID of the conversation.
            query_id: UUID identifying this query execution.
            question: The question text that was asked.
            response: Optional structured response from the AI.
            tools_invoked: Optional list of tools used during execution.
            sources_consulted: Optional list of sources referenced.
            is_partial: Whether the response is incomplete.
            llm_provider: LLM provider used (e.g., "openai").
            llm_model: LLM model used (e.g., "gpt-4").
            prompt_version: Version of the prompt template used.
            duration_ms: Execution duration in milliseconds.

        Returns:
            Dictionary with query history fields.

        Raises:
            ProjectNotFoundError: If the project does not exist.
        """
        project = await self._project_repo.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id=str(project_id))

        query_history = QueryHistory(
            query_id=query_id,
            conversation_id=conversation_id,
            project_id=project_id,
            question=question,
            response=response,
            tools_invoked=tools_invoked,
            sources_consulted=sources_consulted,
            is_partial=is_partial,
            llm_provider=llm_provider,
            llm_model=llm_model,
            prompt_version=prompt_version,
            duration_ms=duration_ms,
        )

        created = await self._query_history_repo.create_query_history(query_history)

        logger.info(
            "query_history_created",
            query_history_id=str(created.id),
            project_id=str(project_id),
            query_id=str(query_id),
        )

        return self._history_to_response(created)

    async def get_query_history(self, query_history_id: UUID) -> dict:
        """
        Retrieve a query history record by ID.

        Args:
            query_history_id: UUID of the query history record.

        Returns:
            Dictionary with query history fields.

        Raises:
            QueryHistoryNotFoundError: If the record does not exist.
        """
        record = await self._query_history_repo.get_query_history(query_history_id)

        if record is None:
            logger.info(
                "query_history_not_found",
                query_history_id=str(query_history_id),
            )
            raise QueryHistoryNotFoundError(query_id=str(query_history_id))

        return self._history_to_response(record)

    async def list_by_project(self, project_id: UUID) -> list[dict]:
        """
        List query history records for a project, ordered newest first.

        Args:
            project_id: UUID of the project.

        Returns:
            List of query history dictionaries ordered by created_at descending.
        """
        records = await self._query_history_repo.list_by_project(project_id)

        logger.debug(
            "query_history_listed",
            project_id=str(project_id),
            total=len(records),
        )

        return [self._history_to_response(r) for r in records]

    # --- Saved Queries ---

    async def create_saved_query(
        self,
        project_id: UUID,
        title: str,
        question: str,
    ) -> dict:
        """
        Create a new saved query for a project.

        Uses SYSTEM_USER_ID as user_id until authentication is implemented.

        Args:
            project_id: UUID of the project.
            title: Display title for the saved query.
            question: The question text to save.

        Returns:
            Dictionary with saved query fields.

        Raises:
            ProjectNotFoundError: If the project does not exist.
        """
        project = await self._project_repo.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id=str(project_id))

        saved_query = SavedQuery(
            user_id=SYSTEM_USER_ID,
            project_id=project_id,
            title=title,
            question=question,
        )

        created = await self._query_history_repo.create_saved_query(saved_query)

        logger.info(
            "saved_query_created",
            saved_query_id=str(created.id),
            project_id=str(project_id),
        )

        return self._saved_to_response(created)

    async def list_saved_by_project(self, project_id: UUID) -> list[dict]:
        """
        List all saved queries for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of saved query dictionaries.
        """
        saved_queries = await self._query_history_repo.list_saved_by_project(project_id)

        return [self._saved_to_response(sq) for sq in saved_queries]

    async def delete_saved_query(self, saved_query_id: UUID) -> None:
        """
        Delete a saved query by ID.

        Args:
            saved_query_id: UUID of the saved query to delete.

        Raises:
            SavedQueryNotFoundError: If the saved query does not exist.
        """
        deleted = await self._query_history_repo.delete_saved_query(saved_query_id)

        if not deleted:
            logger.info(
                "saved_query_not_found_for_delete",
                saved_query_id=str(saved_query_id),
            )
            raise SavedQueryNotFoundError(saved_query_id=str(saved_query_id))

        logger.info(
            "saved_query_deleted",
            saved_query_id=str(saved_query_id),
        )

    # --- Private Helpers ---

    def _history_to_response(self, record: QueryHistory) -> dict:
        """Convert a QueryHistory model to a response dict."""
        return {
            "id": record.id,
            "query_id": record.query_id,
            "conversation_id": record.conversation_id,
            "project_id": record.project_id,
            "question": record.question,
            "response": record.response,
            "tools_invoked": record.tools_invoked,
            "sources_consulted": record.sources_consulted,
            "is_partial": record.is_partial,
            "llm_provider": record.llm_provider,
            "llm_model": record.llm_model,
            "prompt_version": record.prompt_version,
            "duration_ms": record.duration_ms,
            "created_at": record.created_at,
        }

    def _saved_to_response(self, saved_query: SavedQuery) -> dict:
        """Convert a SavedQuery model to a response dict."""
        return {
            "id": saved_query.id,
            "user_id": saved_query.user_id,
            "project_id": saved_query.project_id,
            "title": saved_query.title,
            "question": saved_query.question,
            "created_at": saved_query.created_at,
        }
