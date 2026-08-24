"""
Security validation tests for Phase 8 — Credential Protection.

Validates Requirements 14.1–14.6:
- No credentials in API responses (schemas)
- No credentials passed to AI agent (connector tools)
- No credentials in evidence items or lineage traces
- Credential masking on data source responses

These tests confirm that the Phase 8 response models, tool interfaces,
and orchestration layer never expose sensitive information.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from app.ai.evidence_builder import EvidenceBuilder
from app.ai.lineage_recorder import LineageRecorder
from app.ai.trace import sanitize_log_value


# =============================================================================
# Sensitive patterns — anything that should NEVER appear in responses
# =============================================================================

CREDENTIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)password\s*[:=]\s*\S+"),
    re.compile(r"(?i)(api[_-]?key|secret[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"postgresql(\+\w+)?://\S+:\S+@"),
    re.compile(r"mongodb(\+srv)?://\S+:\S+@"),
    re.compile(r"(?i)bearer\s+\S{20,}"),
]


def _contains_credentials(data: Any) -> bool:
    """Recursively check if any string value contains credential patterns."""
    if isinstance(data, str):
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(data):
                return True
        return False
    elif isinstance(data, dict):
        return any(_contains_credentials(v) for v in data.values())
    elif isinstance(data, (list, tuple)):
        return any(_contains_credentials(item) for item in data)
    return False


# =============================================================================
# Tests: EvidenceBuilder never includes credentials
# =============================================================================


class TestEvidenceBuilderCredentialProtection:
    """Requirement 14.1: No credentials in evidence items."""

    def test_database_evidence_has_no_credential_fields(self) -> None:
        """EvidenceBuilder output for database results contains only business data."""
        builder = EvidenceBuilder()

        tool_result = {
            "columns": ["project_id", "budget", "actual_cost"],
            "rows": [["proj-1", 500000, 480000]],
            "row_count": 1,
            "source_metadata": {
                "source_id": "src-123",
                "source_type": "postgresql",
                "source_name": "Finance DB",
                "object_name": "project_finance",
            },
            "duration_ms": 150,
        }

        evidence = builder.build_evidence([tool_result])

        assert len(evidence) == 1
        item = evidence[0]

        # Verify no credential-like keys exist
        forbidden_keys = {
            "connection_config", "connection_string", "password",
            "api_key", "token", "secret", "credentials",
        }
        assert not forbidden_keys.intersection(item.keys())

        # Verify no credential values in any field
        assert not _contains_credentials(item)

    def test_document_evidence_has_no_credential_fields(self) -> None:
        """EvidenceBuilder output for document results contains only content data."""
        builder = EvidenceBuilder()

        tool_result = {
            "document_id": "doc-456",
            "file_name": "project_plan.pdf",
            "page_number": 3,
            "section": "Budget Summary",
            "excerpt": "The project budget is $500,000.",
        }

        evidence = builder.build_evidence([tool_result])

        assert len(evidence) == 1
        item = evidence[0]

        forbidden_keys = {
            "connection_config", "connection_string", "password",
            "api_key", "token", "secret", "credentials",
        }
        assert not forbidden_keys.intersection(item.keys())
        assert not _contains_credentials(item)

    def test_error_results_produce_no_evidence(self) -> None:
        """Failed tool results do not generate fabricated evidence."""
        builder = EvidenceBuilder()

        error_result = {
            "error": True,
            "error_type": "query_execution_error",
            "message": "Connection timeout",
        }

        evidence = builder.build_evidence([error_result])
        assert evidence == []


# =============================================================================
# Tests: LineageRecorder never includes credentials
# =============================================================================


class TestLineageRecorderCredentialProtection:
    """Requirement 14.1, 14.3: No credentials in lineage traces."""

    def test_lineage_trace_contains_no_credentials(self) -> None:
        """Lineage trace includes only operational metadata, not credentials."""
        from uuid import uuid4

        recorder = LineageRecorder()
        query_id = uuid4()
        recorder.start_trace(query_id, "What is the project budget?")

        recorder.record_catalog_lookup(
            entries_found=5, entries_used=3, duration_ms=45
        )
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-123",
            source_name="Finance PostgreSQL",
            object_name="project_finance",
            status="success",
            duration_ms=200,
            records_count=10,
        )
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-456",
            source_name="Risk MongoDB",
            object_name="project_risks",
            status="failed",
            duration_ms=30000,
            records_count=0,
            error="Connection timeout after 30s",
        )

        trace = recorder.finalize_trace(answer_generated=True)

        # Verify no credential-like values in the entire trace structure
        assert not _contains_credentials(trace)

        # Verify the trace structure doesn't contain credential fields
        for step in trace["steps"]:
            forbidden_keys = {
                "connection_config", "connection_string", "password",
                "api_key", "token", "secret", "credentials",
            }
            assert not forbidden_keys.intersection(step.keys())


# =============================================================================
# Tests: Connector tools interface — source_id only, no credentials
# =============================================================================


class TestConnectorToolsCredentialProtection:
    """Requirement 14.2: Agent receives source_id only, credentials resolved server-side."""

    def test_query_tool_signature_accepts_source_id_only(self) -> None:
        """The query_connected_source tool accepts source_id, not credentials."""
        from app.ai.tools.connector_tools import query_connected_source

        # Verify the tool function exists and its parameters don't accept credentials
        import inspect

        sig = inspect.signature(query_connected_source.__wrapped__)
        param_names = set(sig.parameters.keys())

        # Should accept source_id, query_type, query — NOT credentials
        credential_params = {
            "password", "connection_string", "api_key", "token",
            "credentials", "connection_config",
        }
        assert not credential_params.intersection(param_names), (
            f"Tool function should not accept credential parameters. "
            f"Found: {credential_params.intersection(param_names)}"
        )

    def test_discover_tool_signature_accepts_project_id_only(self) -> None:
        """The discover_available_sources tool accepts project_id, not credentials."""
        from app.ai.tools.connector_tools import discover_available_sources

        import inspect

        sig = inspect.signature(discover_available_sources.__wrapped__)
        param_names = set(sig.parameters.keys())

        credential_params = {
            "password", "connection_string", "api_key", "token",
            "credentials", "connection_config",
        }
        assert not credential_params.intersection(param_names)


# =============================================================================
# Tests: Sanitize log value redacts credentials
# =============================================================================


class TestSanitizeLogValue:
    """Requirement 14.3: Credentials never appear in logs or error responses."""

    def test_redacts_postgresql_connection_string(self) -> None:
        """Connection strings in exceptions are redacted."""
        raw_error = (
            "could not connect to server: "
            "postgresql+asyncpg://admin:s3cr3t_p@ss@db.example.com:5432/finance"
        )
        sanitized = sanitize_log_value(raw_error)
        assert "s3cr3t_p@ss" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_redacts_mongodb_connection_string(self) -> None:
        """MongoDB URIs with credentials are redacted."""
        raw_error = "Authentication failed: mongodb+srv://user:password123@cluster.mongodb.net/db"
        sanitized = sanitize_log_value(raw_error)
        assert "password123" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_redacts_password_field(self) -> None:
        """Inline password references are redacted."""
        raw_error = "Config error: password=my_secret_password"
        sanitized = sanitize_log_value(raw_error)
        assert "my_secret_password" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_preserves_safe_error_messages(self) -> None:
        """Non-credential error messages are not altered."""
        safe_error = "Connection timeout after 30 seconds"
        sanitized = sanitize_log_value(safe_error)
        assert sanitized == safe_error


# =============================================================================
# Tests: CatalogEntryResponse schema has no credential fields
# =============================================================================


class TestCatalogResponseCredentialProtection:
    """Requirement 14.1, 14.4: No credentials in catalog API responses."""

    def test_catalog_entry_response_has_no_credential_fields(self) -> None:
        """CatalogEntryResponse schema contains only metadata fields."""
        from app.schemas.catalog import CatalogEntryResponse

        field_names = set(CatalogEntryResponse.model_fields.keys())

        credential_fields = {
            "connection_config", "connection_string", "password",
            "api_key", "token", "secret", "credentials",
            "private_key", "fernet_key",
        }
        leaked = credential_fields.intersection(field_names)
        assert not leaked, (
            f"CatalogEntryResponse must not contain credential fields. Found: {leaked}"
        )

    def test_discovery_result_response_has_no_credential_fields(self) -> None:
        """DiscoveryResultResponse schema contains only operational metadata."""
        from app.schemas.catalog import DiscoveryResultResponse

        field_names = set(DiscoveryResultResponse.model_fields.keys())

        credential_fields = {
            "connection_config", "connection_string", "password",
            "api_key", "token", "secret", "credentials",
            "private_key", "fernet_key",
        }
        leaked = credential_fields.intersection(field_names)
        assert not leaked, (
            f"DiscoveryResultResponse must not contain credential fields. Found: {leaked}"
        )

    def test_discovery_result_response_has_no_raw_schema(self) -> None:
        """DiscoveryResultResponse does not include raw schema with potential connection info."""
        from app.schemas.catalog import DiscoveryResultResponse

        field_names = set(DiscoveryResultResponse.model_fields.keys())

        # Should not include raw schema details that could contain connection info
        assert "connection_config" not in field_names
        assert "raw_schema" not in field_names


# =============================================================================
# Tests: DataSourceResponse uses masked credentials
# =============================================================================


class TestDataSourceResponseMasking:
    """Requirement 14.4: Data source responses use *_configured booleans."""

    def test_data_source_response_documents_masking(self) -> None:
        """DataSourceResponse documents that connection_config is masked."""
        from app.schemas.data_source import DataSourceResponse

        # The connection_config field description should mention masking
        field_info = DataSourceResponse.model_fields["connection_config"]
        description = field_info.description or ""
        assert "mask_config" in description or "*_configured" in description or "Non-sensitive" in description
