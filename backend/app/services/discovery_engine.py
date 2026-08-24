"""
DiscoveryEngine — orchestrates schema discovery and semantic profiling.

Responsible for introspecting connected data sources and populating the
Enterprise Data Catalog with both technical and semantic metadata.
All discovery operations are READ-ONLY — the engine never modifies
external sources.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.trace import sanitize_log_value
from app.connectors.protocol import (
    FieldInfo,
    SchemaInfo,
    TableSchema,
)
from app.connectors.registry import ConnectorRegistry
from app.models.catalog_entry import CatalogEntry
from app.models.data_source import DataSource
from app.schemas.discovery import SemanticProfile
from app.services.catalog_service import CatalogService
from app.services.semantic_profiler import SemanticMetadataProfiler

logger = structlog.get_logger(__name__)

# Patterns that indicate sensitive fields — never sampled or exposed.
SENSITIVE_FIELD_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(password|passwd|pwd)"),
    re.compile(r"(?i)(secret|api_?key|access_?key)"),
    re.compile(r"(?i)(token|auth_?token|refresh_?token|jwt)"),
    re.compile(r"(?i)(private_?key|priv_?key|ssh_?key)"),
    re.compile(r"(?i)(credential|cred)"),
    re.compile(r"(?i)(connection_?string|conn_?str)"),
]

# Default configurable limits
DEFAULT_SAMPLE_SIZE = 100
DEFAULT_MAX_TABLES = 200
DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class DiscoveryResult:
    """Summary of a discovery operation."""

    source_id: UUID
    success: bool
    objects_discovered: int
    fields_discovered: int
    relationships_discovered: int
    project_fields_found: list[str] = field(default_factory=list)
    duration_ms: int = 0
    error: str | None = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DiscoveryEngine:
    """Orchestrates schema discovery and semantic profiling for connected data sources.

    The Discovery Engine is the foundation of the Enterprise Data Catalog.
    When a source is connected, it discovers structure, profiles metadata,
    generates semantic understanding, and persists the catalog.

    All operations are read-only — external sources are never modified.
    """

    def __init__(
        self,
        connector_registry: ConnectorRegistry,
        catalog_service: CatalogService,
        semantic_profiler: SemanticMetadataProfiler,
        session: AsyncSession,
    ) -> None:
        self._connector_registry = connector_registry
        self._catalog_service = catalog_service
        self._semantic_profiler = semantic_profiler
        self._session = session

    async def discover_source(
        self, source_id: UUID, data_source: DataSource
    ) -> DiscoveryResult:
        """Run full discovery on a data source.

        Flow:
        1. Get connector from ConnectorRegistry
        2. Test connection
        3. Discover schema (tables/collections/fields/types)
        4. Profile each discovered object semantically
        5. Build CatalogEntry instances
        6. Store entries via CatalogService
        7. Update DataSource status fields
        8. Return DiscoveryResult summary

        On failure: set discovery_status="failed", preserve previous catalog.
        """
        start_time = time.perf_counter()

        try:
            # 1. Get connector
            connector = self._connector_registry.resolve(
                data_source.source_type,
                data_source.connection_config,
            )

            # 2. Test connection
            is_connected = await connector.test_connection()
            if not is_connected:
                raise ConnectionError(
                    f"Connection test failed for source '{data_source.name}'"
                )

            logger.info(
                "discovery_connection_verified",
                source_id=str(source_id),
                source_type=data_source.source_type,
            )

            # 3. Discover schema
            schema: SchemaInfo = await connector.discover_schema()

            logger.info(
                "discovery_schema_extracted",
                source_id=str(source_id),
                tables_found=len(schema.tables),
            )

            # 4. Semantic profiling for each table/collection
            profiles: list[SemanticProfile] = []
            for table in schema.tables:
                profile = await self._profile_object(
                    table, data_source.source_type, data_source
                )
                profiles.append(profile)

            # 5. Build catalog entries
            catalog_entries = self._build_catalog_entries(
                source_id=source_id,
                schema=schema,
                profiles=profiles,
                source_type=data_source.source_type,
            )

            # 6. Store entries via catalog service
            stored_count = await self._catalog_service.store_discovery_results(
                source_id, catalog_entries
            )

            # Compute totals
            total_fields = sum(len(t.fields) for t in schema.tables)
            all_project_fields = self._collect_project_fields(profiles)

            # 7. Update data source status
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            data_source.last_discovery_at = datetime.now(timezone.utc)
            data_source.discovery_status = "completed"
            data_source.objects_discovered = len(schema.tables)
            data_source.fields_discovered = total_fields
            data_source.discovery_error = None
            await self._session.flush()

            logger.info(
                "discovery_completed",
                source_id=str(source_id),
                objects_discovered=len(schema.tables),
                fields_discovered=total_fields,
                entries_stored=stored_count,
                duration_ms=elapsed_ms,
            )

            # 8. Return result
            return DiscoveryResult(
                source_id=source_id,
                success=True,
                objects_discovered=len(schema.tables),
                fields_discovered=total_fields,
                relationships_discovered=0,
                project_fields_found=all_project_fields,
                duration_ms=elapsed_ms,
                discovered_at=datetime.now(timezone.utc),
            )

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            # Sanitize error message to prevent credential leakage via DB driver exceptions
            error_message = sanitize_log_value(str(exc))

            logger.error(
                "discovery_failed",
                source_id=str(source_id),
                error=error_message,
                duration_ms=elapsed_ms,
            )

            # Update data source status — preserve previous catalog
            data_source.discovery_status = "failed"
            data_source.discovery_error = error_message
            await self._session.flush()

            return DiscoveryResult(
                source_id=source_id,
                success=False,
                objects_discovered=0,
                fields_discovered=0,
                relationships_discovered=0,
                duration_ms=elapsed_ms,
                error=error_message,
                discovered_at=datetime.now(timezone.utc),
            )

    async def refresh_source(
        self, source_id: UUID, data_source: DataSource
    ) -> DiscoveryResult:
        """Re-run discovery, preserving previous catalog on failure.

        Delegates to discover_source which already preserves the previous
        catalog on failure (it only stores new entries on success).
        """
        return await self.discover_source(source_id, data_source)

    def _build_catalog_entries(
        self,
        source_id: UUID,
        schema: SchemaInfo,
        profiles: list[SemanticProfile],
        source_type: str,
    ) -> list[CatalogEntry]:
        """Construct CatalogEntry model instances from discovery data.

        Combines technical schema with semantic profiles to produce
        fully enriched catalog entries ready for persistence.
        """
        entries: list[CatalogEntry] = []
        now = datetime.now(timezone.utc)

        for table, profile in zip(schema.tables, profiles):
            # Build field metadata with sensitive detection
            fields_json = self._build_fields_json(table.fields, profile)

            # Determine object type from source type
            object_type = self._infer_object_type(source_type)

            entry = CatalogEntry(
                id=uuid4(),
                source_id=source_id,
                object_name=table.name,
                object_type=object_type,
                fields=fields_json,
                primary_keys=[],
                foreign_keys=[],
                indexes=[],
                # Semantic metadata from profiler
                semantic_name=profile.semantic_name,
                semantic_description=profile.description,
                domain_tags=profile.domain_tags,
                query_capabilities=profile.query_capabilities,
                suggested_queries=profile.suggested_questions,
                confidence=profile.confidence,
                project_fields=profile.project_fields,
                # Versioning (actual version set by CatalogService)
                version=1,
                discovered_at=now,
            )
            entries.append(entry)

        return entries

    def _build_fields_json(
        self, fields: list[FieldInfo], profile: SemanticProfile
    ) -> list[dict]:
        """Build JSON-serializable field metadata with sensitive detection.

        Each field includes:
        - Technical info: name, type, nullable
        - Semantic info: label, description (from profile)
        - Flags: is_sensitive, is_project_field
        """
        # Build lookup from profile's important_fields for semantic enrichment
        semantic_lookup: dict[str, dict] = {}
        for sf in profile.important_fields:
            semantic_lookup[sf.technical_name] = {
                "semantic_label": sf.semantic_label,
                "description": sf.description,
                "is_identifier": sf.is_identifier,
                "is_project_field": sf.is_project_field,
            }

        project_fields_set = set(profile.project_fields)
        result: list[dict] = []

        for f in fields:
            is_sensitive = self._is_sensitive_field(f.name)
            semantic_info = semantic_lookup.get(f.name, {})

            result.append({
                "name": f.name,
                "field_type": f.field_type,
                "nullable": f.nullable,
                "is_primary_key": False,
                "semantic_label": semantic_info.get("semantic_label"),
                "semantic_description": semantic_info.get("description"),
                "is_project_field": f.name in project_fields_set,
                "is_sensitive": is_sensitive,
            })

        return result

    async def _profile_object(
        self,
        table: TableSchema,
        source_type: str,
        data_source: DataSource,
    ) -> SemanticProfile:
        """Profile a single table/collection using the semantic profiler.

        Routes to the appropriate profiler method based on source type.
        """
        if source_type == "mongodb":
            return await self._semantic_profiler.profile_collection(table, data_source)
        else:
            # PostgreSQL and other relational sources
            return await self._semantic_profiler.profile_table(table, data_source)

    def _collect_project_fields(self, profiles: list[SemanticProfile]) -> list[str]:
        """Gather all unique project fields across all profiles."""
        all_fields: set[str] = set()
        for profile in profiles:
            all_fields.update(profile.project_fields)
        return sorted(all_fields)

    @staticmethod
    def _is_sensitive_field(field_name: str) -> bool:
        """Detect if a field name matches sensitive data patterns."""
        for pattern in SENSITIVE_FIELD_PATTERNS:
            if pattern.search(field_name):
                return True
        return False

    @staticmethod
    def _infer_object_type(source_type: str) -> str:
        """Map source type to the default catalog object type."""
        type_mapping = {
            "postgresql": "table",
            "mongodb": "collection",
            "document": "document",
        }
        return type_mapping.get(source_type, "table")
