"""Unit tests for ConnectorService — orchestration, timeout, row-cap, and validation."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.connectors.protocol import QueryResult, SchemaInfo, SourceMetadata, TableSchema
from app.errors.datasource_errors import (
    DataSourceNotFoundError,
    QueryValidationError,
    TimeoutOperationError,
    UnsupportedDataSourceError,
)
from app.services.connector_service import API_OPERATION_TIMEOUT, API_ROW_CAP, ConnectorService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_DATA_SOURCE_ID = uuid4()


@dataclass
class FakeDataSource:
    """Minimal data source model stand-in for testing."""

    id: UUID
    source_type: str
    connection_config: dict[str, Any]


def _build_service(
    repo_return: Any = None,
    decrypt_return: dict | None = None,
    resolve_return: Any = None,
    resolve_side_effect: Exception | None = None,
) -> tuple[ConnectorService, MagicMock, MagicMock, MagicMock]:
    """Construct a ConnectorService with mocked dependencies.

    Returns (service, mock_repo, mock_encryptor, mock_registry).
    """
    mock_repo = AsyncMock()
    mock_repo.get_data_source.return_value = repo_return

    mock_encryptor = MagicMock()
    mock_encryptor.decrypt_config.return_value = decrypt_return or {}

    mock_registry = MagicMock()
    if resolve_side_effect:
        mock_registry.resolve.side_effect = resolve_side_effect
    else:
        mock_registry.resolve.return_value = resolve_return

    service = ConnectorService(
        data_source_repository=mock_repo,
        credential_encryptor=mock_encryptor,
        connector_registry=mock_registry,
    )
    return service, mock_repo, mock_encryptor, mock_registry


# ---------------------------------------------------------------------------
# 1. _resolve_connector tests
# ---------------------------------------------------------------------------


class TestResolveConnector:
    """Verify _resolve_connector resolution, not-found, and unsupported paths."""

    @pytest.mark.asyncio
    async def test_happy_path_returns_connector_and_source_type(self) -> None:
        fake_ds = FakeDataSource(
            id=FAKE_DATA_SOURCE_ID,
            source_type="postgresql",
            connection_config={"host": "db.local", "password": "encrypted"},
        )
        mock_connector = AsyncMock()
        decrypted = {"host": "db.local", "password": "secret"}

        service, mock_repo, mock_encryptor, mock_registry = _build_service(
            repo_return=fake_ds,
            decrypt_return=decrypted,
            resolve_return=mock_connector,
        )

        connector, source_type = await service._resolve_connector(FAKE_DATA_SOURCE_ID)

        assert connector is mock_connector
        assert source_type == "postgresql"
        mock_repo.get_data_source.assert_awaited_once_with(FAKE_DATA_SOURCE_ID)
        mock_encryptor.decrypt_config.assert_called_once_with(fake_ds.connection_config)
        mock_registry.resolve.assert_called_once_with(
            source_type="postgresql",
            connection_config=decrypted,
        )

    @pytest.mark.asyncio
    async def test_not_found_raises_data_source_not_found_error(self) -> None:
        service, _, _, _ = _build_service(repo_return=None)

        with pytest.raises(DataSourceNotFoundError):
            await service._resolve_connector(FAKE_DATA_SOURCE_ID)

    @pytest.mark.asyncio
    async def test_unsupported_type_raises_unsupported_data_source_error(self) -> None:
        fake_ds = FakeDataSource(
            id=FAKE_DATA_SOURCE_ID,
            source_type="oracle",
            connection_config={},
        )
        service, _, _, _ = _build_service(
            repo_return=fake_ds,
            resolve_side_effect=UnsupportedDataSourceError(
                requested_type="oracle", supported_types=["postgresql", "mongodb"]
            ),
        )

        with pytest.raises(UnsupportedDataSourceError) as exc_info:
            await service._resolve_connector(FAKE_DATA_SOURCE_ID)

        assert exc_info.value.requested_type == "oracle"


# ---------------------------------------------------------------------------
# 2. _execute_with_timeout tests
# ---------------------------------------------------------------------------


class TestExecuteWithTimeout:
    """Verify timeout enforcement and success paths."""

    @pytest.mark.asyncio
    async def test_success_path_returns_result(self) -> None:
        service, _, _, _ = _build_service()
        deadline = time.monotonic() + 10  # plenty of budget

        async def fake_coro():
            return "result_value"

        result = await service._execute_with_timeout(
            fake_coro(), operation_name="test_op", deadline=deadline, source_id="test-id"
        )
        assert result == "result_value"

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_operation_error(self) -> None:
        service, _, _, _ = _build_service()
        # Deadline already passed
        deadline = time.monotonic() - 1

        async def fake_coro():
            return "never reached"

        coro = fake_coro()
        with pytest.raises(TimeoutOperationError) as exc_info:
            await service._execute_with_timeout(
                coro, operation_name="discover_schema", deadline=deadline, source_id="test-id"
            )
        # Close the unawaited coroutine to suppress RuntimeWarning
        coro.close()

        assert exc_info.value.operation == "discover_schema"
        assert exc_info.value.timeout_seconds == API_OPERATION_TIMEOUT

    @pytest.mark.asyncio
    async def test_asyncio_timeout_raises_timeout_operation_error(self) -> None:
        service, _, _, _ = _build_service()
        # Very short deadline so asyncio.wait_for triggers
        deadline = time.monotonic() + 0.01

        async def slow_coro():
            await asyncio.sleep(5)
            return "never"

        with pytest.raises(TimeoutOperationError) as exc_info:
            await service._execute_with_timeout(
                slow_coro(), operation_name="execute_query", deadline=deadline, source_id="test-id"
            )

        assert exc_info.value.operation == "execute_query"


# ---------------------------------------------------------------------------
# 3. _apply_row_cap tests
# ---------------------------------------------------------------------------


class TestApplyRowCap:
    """Verify row capping and truncation flag logic."""

    def test_below_cap_no_truncation(self) -> None:
        service, _, _, _ = _build_service()
        result = QueryResult(
            columns=["id"],
            rows=[{"id": i} for i in range(100)],
            row_count=100,
            source_type="postgresql",
            has_more_rows=False,
        )

        capped, truncated = service._apply_row_cap(result)

        assert truncated is False
        assert capped.row_count == 100
        assert len(capped.rows) == 100

    def test_at_cap_with_has_more_rows_true(self) -> None:
        service, _, _, _ = _build_service()
        result = QueryResult(
            columns=["id"],
            rows=[{"id": i} for i in range(API_ROW_CAP)],
            row_count=API_ROW_CAP,
            source_type="postgresql",
            has_more_rows=True,
        )

        capped, truncated = service._apply_row_cap(result)

        assert truncated is True
        assert capped.row_count == API_ROW_CAP
        assert len(capped.rows) == API_ROW_CAP

    def test_above_cap_rows_capped_and_truncated(self) -> None:
        service, _, _, _ = _build_service()
        rows = [{"id": i} for i in range(API_ROW_CAP + 500)]
        result = QueryResult(
            columns=["id"],
            rows=rows,
            row_count=API_ROW_CAP + 500,
            source_type="postgresql",
            has_more_rows=False,
        )

        capped, truncated = service._apply_row_cap(result)

        assert truncated is True
        assert capped.row_count == API_ROW_CAP
        assert len(capped.rows) == API_ROW_CAP
        assert capped.has_more_rows is True


# ---------------------------------------------------------------------------
# 4. Orchestration: discover_metadata / discover_schema / execute_query
# ---------------------------------------------------------------------------


class TestOrchestration:
    """Verify end-to-end orchestration with mocked connector."""

    @pytest.mark.asyncio
    async def test_discover_metadata_returns_source_metadata(self) -> None:
        expected = SourceMetadata(
            source_type="postgresql", name="finance_db", version="15.2"
        )
        mock_connector = AsyncMock()
        mock_connector.discover_metadata.return_value = expected

        fake_ds = FakeDataSource(
            id=FAKE_DATA_SOURCE_ID,
            source_type="postgresql",
            connection_config={"host": "localhost"},
        )
        service, _, _, _ = _build_service(
            repo_return=fake_ds,
            decrypt_return={"host": "localhost"},
            resolve_return=mock_connector,
        )

        result = await service.discover_metadata(FAKE_DATA_SOURCE_ID)

        assert result == expected
        mock_connector.discover_metadata.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_discover_schema_returns_schema_info(self) -> None:
        expected = SchemaInfo(tables=[TableSchema(name="public.users", fields=[])])
        mock_connector = AsyncMock()
        mock_connector.discover_schema.return_value = expected

        fake_ds = FakeDataSource(
            id=FAKE_DATA_SOURCE_ID,
            source_type="postgresql",
            connection_config={"host": "localhost"},
        )
        service, _, _, _ = _build_service(
            repo_return=fake_ds,
            decrypt_return={"host": "localhost"},
            resolve_return=mock_connector,
        )

        result = await service.discover_schema(FAKE_DATA_SOURCE_ID)

        assert result == expected
        mock_connector.discover_schema.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_query_returns_result_and_truncated_flag(self) -> None:
        query_result = QueryResult(
            columns=["name", "amount"],
            rows=[{"name": "Budget A", "amount": 1000}],
            row_count=1,
            source_type="postgresql",
            has_more_rows=False,
        )
        mock_connector = AsyncMock()
        mock_connector.execute_read.return_value = query_result

        fake_ds = FakeDataSource(
            id=FAKE_DATA_SOURCE_ID,
            source_type="postgresql",
            connection_config={"host": "localhost"},
        )
        service, _, _, _ = _build_service(
            repo_return=fake_ds,
            decrypt_return={"host": "localhost"},
            resolve_return=mock_connector,
        )

        result, truncated = await service.execute_query(
            FAKE_DATA_SOURCE_ID, "SELECT * FROM budgets"
        )

        assert result == query_result
        assert truncated is False
        mock_connector.execute_read.assert_awaited_once_with("SELECT * FROM budgets")


# ---------------------------------------------------------------------------
# 5. Source-type query type validation
# ---------------------------------------------------------------------------


class TestQueryTypeValidation:
    """Verify wrong query types are rejected with QueryValidationError."""

    @pytest.mark.asyncio
    async def test_str_query_with_mongodb_raises_validation_error(self) -> None:
        mock_connector = AsyncMock()
        fake_ds = FakeDataSource(
            id=FAKE_DATA_SOURCE_ID,
            source_type="mongodb",
            connection_config={"uri": "mongodb://localhost"},
        )
        service, _, _, _ = _build_service(
            repo_return=fake_ds,
            decrypt_return={"uri": "mongodb://localhost"},
            resolve_return=mock_connector,
        )

        with pytest.raises(QueryValidationError) as exc_info:
            await service.execute_query(FAKE_DATA_SOURCE_ID, "SELECT * FROM users")

        assert exc_info.value.source_type == "mongodb"
        assert "dictionaries" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_dict_query_with_postgresql_raises_validation_error(self) -> None:
        mock_connector = AsyncMock()
        fake_ds = FakeDataSource(
            id=FAKE_DATA_SOURCE_ID,
            source_type="postgresql",
            connection_config={"host": "localhost"},
        )
        service, _, _, _ = _build_service(
            repo_return=fake_ds,
            decrypt_return={"host": "localhost"},
            resolve_return=mock_connector,
        )

        with pytest.raises(QueryValidationError) as exc_info:
            await service.execute_query(
                FAKE_DATA_SOURCE_ID, {"collection": "users", "filter": {}}
            )

        assert exc_info.value.source_type == "postgresql"
        assert "SQL strings" in exc_info.value.message


# ---------------------------------------------------------------------------
# 6. Timeout budget propagation
# ---------------------------------------------------------------------------


class TestTimeoutBudgetPropagation:
    """Verify remaining deadline is less than 30s after resolution overhead."""

    @pytest.mark.asyncio
    async def test_remaining_budget_less_than_30s_after_resolution(self) -> None:
        """After _resolve_connector completes, the remaining deadline passed to
        _execute_with_timeout should be less than the full 30s budget."""
        captured_deadline: list[float] = []

        mock_connector = AsyncMock()
        mock_connector.discover_metadata.return_value = SourceMetadata(
            source_type="postgresql", name="test", version="15"
        )

        fake_ds = FakeDataSource(
            id=FAKE_DATA_SOURCE_ID,
            source_type="postgresql",
            connection_config={"host": "localhost"},
        )
        service, _, _, _ = _build_service(
            repo_return=fake_ds,
            decrypt_return={"host": "localhost"},
            resolve_return=mock_connector,
        )

        original_execute = service._execute_with_timeout

        async def capture_deadline(coro, operation_name, deadline, source_id):
            remaining = deadline - time.monotonic()
            captured_deadline.append(remaining)
            return await original_execute(coro, operation_name, deadline, source_id)

        with patch.object(service, "_execute_with_timeout", side_effect=capture_deadline):
            await service.discover_metadata(FAKE_DATA_SOURCE_ID)

        # After resolution overhead, remaining must be < 30s
        assert len(captured_deadline) == 1
        assert captured_deadline[0] < API_OPERATION_TIMEOUT


# ---------------------------------------------------------------------------
# 7. Credential scope — decrypted config does not persist on service instance
# ---------------------------------------------------------------------------


class TestCredentialScope:
    """Verify decrypted credentials do not persist on the service after operations."""

    @pytest.mark.asyncio
    async def test_decrypted_config_not_stored_on_service(self) -> None:
        """After _resolve_connector completes, no decrypted credentials should
        be accessible as an attribute on the ConnectorService instance."""
        decrypted_secrets = {"host": "db.local", "password": "super_secret_password"}

        mock_connector = AsyncMock()
        mock_connector.discover_metadata.return_value = SourceMetadata(
            source_type="postgresql", name="test", version="15"
        )

        fake_ds = FakeDataSource(
            id=FAKE_DATA_SOURCE_ID,
            source_type="postgresql",
            connection_config={"host": "db.local", "password": "encrypted_value"},
        )
        service, _, mock_encryptor, _ = _build_service(
            repo_return=fake_ds,
            decrypt_return=decrypted_secrets,
            resolve_return=mock_connector,
        )

        await service.discover_metadata(FAKE_DATA_SOURCE_ID)

        # Verify no decrypted config is stored on the service instance
        for attr_name in dir(service):
            attr_value = getattr(service, attr_name, None)
            if isinstance(attr_value, dict):
                assert "super_secret_password" not in str(attr_value), (
                    f"Decrypted credential found in service attribute '{attr_name}'"
                )

        # The service should not have any attribute storing the decrypted config
        assert not hasattr(service, "_decrypted_config")
        assert not hasattr(service, "decrypted_config")
        assert not hasattr(service, "_connection_config")
