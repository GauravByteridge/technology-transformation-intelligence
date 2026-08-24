"""
CatalogContextInjector — builds catalog-aware context for the Strands Agent.

Selects relevant catalog metadata based on the user's question and project
context, and formats it as a semantic information landscape for the LLM system
prompt. The LLM never receives the entire enterprise catalog — only entries
relevant to the current question and project.

The output presents information by domain (Finance, Risk, Resources, etc.)
so the LLM understands WHAT data is available and its business meaning,
not just which database technologies are connected.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from app.models.catalog_entry import CatalogEntry
from app.services.catalog_service import CatalogService

logger = logging.getLogger(__name__)


@dataclass
class CatalogContext:
    """Curated catalog context for injection into the Strands Agent prompt.

    Attributes:
        entries: Ranked list of catalog entries relevant to the question/project.
        project_id: The project scope used, if any.
        total_available: Total catalog entries that exist across all sources.
        included_count: Number of entries included in this context window.
    """

    entries: list[CatalogEntry] = field(default_factory=list)
    project_id: UUID | None = None
    total_available: int = 0
    included_count: int = 0


class CatalogContextInjector:
    """Builds catalog-aware context for the Strands Agent.

    Does NOT inject the entire enterprise catalog. Instead:
    1. Searches the catalog for entries relevant to the question/project
    2. Ranks by relevance (project-mapped entries get priority)
    3. Limits context size to prevent prompt bloat
    4. Formats as a semantic information landscape (not just DB names)

    The LLM receives information like:
    - "Finance (PostgreSQL - project_finance): Project budget, actual cost, variance"
    - "Project Risks (MongoDB - project_risks): Risk severity, status, descriptions"
    - "Meeting Notes (RAG - documents): Project meeting notes and decisions"

    Rather than just:
    - "PostgreSQL is connected"
    - "MongoDB is connected"
    """

    def __init__(
        self,
        catalog_service: CatalogService,
        max_context_entries: int = 20,
    ) -> None:
        """Initialize the injector with the catalog service.

        Args:
            catalog_service: Service for catalog retrieval and search.
            max_context_entries: Maximum catalog entries to include in prompt context.
        """
        self._catalog_service = catalog_service
        self._max_context_entries = max_context_entries

    async def build_relevant_context(
        self, question: str, project_id: UUID | None = None
    ) -> CatalogContext:
        """Build relevant catalog context for a specific question.

        Flow:
        1. If project_id provided, get project-mapped entries
        2. Search catalog by question keywords
        3. Combine and deduplicate (project entries first, then search results)
        4. Rank by relevance (project-mapped entries get priority)
        5. Limit to max_context_entries
        6. Return CatalogContext with entries and metadata

        Args:
            question: The user's natural-language question.
            project_id: Optional project UUID to scope and prioritize results.

        Returns:
            CatalogContext containing ranked, deduplicated entries.
        """
        project_entries: list[CatalogEntry] = []
        search_entries: list[CatalogEntry] = []

        # Step 1: Get project-mapped entries if project_id is provided
        if project_id is not None:
            project_entries = await self._catalog_service.get_catalog_for_project(
                project_id
            )
            logger.debug(
                "catalog_context_project_entries",
                extra={
                    "project_id": str(project_id),
                    "entry_count": len(project_entries),
                },
            )

        # Step 2: Search catalog by question keywords
        search_entries = await self._catalog_service.search_catalog(
            query=question, project_id=project_id
        )
        logger.debug(
            "catalog_context_search_results",
            extra={
                "query": question[:100],
                "result_count": len(search_entries),
            },
        )

        # Step 3: Combine and deduplicate (project entries first)
        combined = self._deduplicate_entries(project_entries, search_entries)

        # Step 4: Total available before limiting
        total_available = len(combined)

        # Step 5: Limit to max_context_entries
        limited = combined[: self._max_context_entries]

        logger.info(
            "catalog_context_built",
            extra={
                "project_id": str(project_id) if project_id else None,
                "total_available": total_available,
                "included_count": len(limited),
                "max_allowed": self._max_context_entries,
            },
        )

        return CatalogContext(
            entries=limited,
            project_id=project_id,
            total_available=total_available,
            included_count=len(limited),
        )

    def format_for_system_prompt(self, context: CatalogContext) -> str:
        """Format catalog context as a semantic information landscape for the system prompt.

        Presents information by domain (not just database type):

        "Available Enterprise Data Sources:

        Finance (PostgreSQL - project_finance):
        Project budget, actual cost, and variance information.
        Key fields: project_id, budget, actual_cost, variance
        Capabilities: budget analysis, cost tracking

        Project Risks (MongoDB - project_risks):
        Current and historical project risk observations.
        Key fields: project_id, severity, status, description
        Capabilities: risk tracking, severity analysis

        Meeting Notes (RAG - documents):
        Project meeting notes and decisions.
        Capabilities: full text search, section search"

        Args:
            context: The CatalogContext with ranked relevant entries.

        Returns:
            Formatted string for inclusion in the Strands Agent system prompt.
        """
        if not context.entries:
            return "No enterprise data sources are currently available."

        sections: list[str] = []
        sections.append("Available Enterprise Data Sources:")
        sections.append("")

        for entry in context.entries:
            entry_section = self._format_entry(entry)
            sections.append(entry_section)

        # Add summary footer if entries were truncated
        if context.total_available > context.included_count:
            sections.append(
                f"({context.total_available - context.included_count} additional "
                f"sources available but not shown)"
            )

        return "\n".join(sections)

    def _deduplicate_entries(
        self,
        project_entries: list[CatalogEntry],
        search_entries: list[CatalogEntry],
    ) -> list[CatalogEntry]:
        """Combine and deduplicate entries, preserving project entries first.

        Project-mapped entries are prioritized (listed first) because they have
        a known relationship to the user's project context. Search results that
        aren't already in the project set are appended after.

        Args:
            project_entries: Entries with confirmed project mappings.
            search_entries: Entries found via keyword/semantic search.

        Returns:
            Deduplicated list with project entries first.
        """
        seen_ids: set[UUID] = set()
        combined: list[CatalogEntry] = []

        # Project-mapped entries get priority placement
        for entry in project_entries:
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                combined.append(entry)

        # Search results added after, skipping duplicates
        for entry in search_entries:
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                combined.append(entry)

        return combined

    def _format_entry(self, entry: CatalogEntry) -> str:
        """Format a single catalog entry as a readable prompt section.

        Args:
            entry: The catalog entry to format.

        Returns:
            Multi-line string describing the entry's domain, capabilities, and fields.
        """
        # Build the header: semantic name or fallback to object name
        display_name = entry.semantic_name or entry.object_name

        # Determine source type label
        source_type_label = self._get_source_type_label(entry)

        # Header line: "Domain (SourceType - object_name):"
        header = f"{display_name} ({source_type_label} - {entry.object_name}):"

        lines: list[str] = [header]

        # Description
        if entry.semantic_description:
            lines.append(entry.semantic_description)

        # Key fields (extract field names from the JSONB fields list)
        field_names = self._extract_field_names(entry)
        if field_names:
            fields_str = ", ".join(field_names[:8])
            lines.append(f"Key fields: {fields_str}")

        # Query capabilities
        capabilities = entry.query_capabilities or []
        if capabilities:
            capabilities_str = ", ".join(capabilities[:6])
            lines.append(f"Capabilities: {capabilities_str}")

        # Domain tags for additional context
        domain_tags = entry.domain_tags or []
        if domain_tags:
            tags_str = ", ".join(domain_tags[:5])
            lines.append(f"Domain: {tags_str}")

        # Add trailing blank line for readability
        lines.append("")

        return "\n".join(lines)

    def _get_source_type_label(self, entry: CatalogEntry) -> str:
        """Map object_type/source info to a human-readable source type label.

        Args:
            entry: The catalog entry.

        Returns:
            A label like "PostgreSQL", "MongoDB", or "RAG".
        """
        # Use the data_source relationship if loaded
        if entry.data_source is not None:
            source_type = entry.data_source.source_type
            if source_type == "postgresql":
                return "PostgreSQL"
            elif source_type == "mongodb":
                return "MongoDB"
            elif source_type in ("document", "rag"):
                return "RAG"
            else:
                return source_type.capitalize()

        # Fallback based on object_type
        object_type = entry.object_type or ""
        if object_type in ("table", "view"):
            return "PostgreSQL"
        elif object_type == "collection":
            return "MongoDB"
        elif object_type == "document":
            return "RAG"
        else:
            return "Unknown"

    def _extract_field_names(self, entry: CatalogEntry) -> list[str]:
        """Extract field names from a catalog entry's fields JSONB.

        The fields column stores a list of field dicts with at minimum a 'name' key.
        Prioritizes project fields and semantically-labeled fields.

        Args:
            entry: The catalog entry.

        Returns:
            List of field names, ordered with important fields first.
        """
        fields_data = entry.fields or []
        if not isinstance(fields_data, list):
            return []

        important_fields: list[str] = []
        other_fields: list[str] = []

        for field_def in fields_data:
            if not isinstance(field_def, dict):
                continue

            name = field_def.get("name", "")
            if not name:
                continue

            # Prioritize project fields and primary keys
            is_project_field = field_def.get("is_project_field", False)
            is_pk = field_def.get("is_primary_key", False)
            has_semantic = field_def.get("semantic_label") is not None

            if is_project_field or is_pk or has_semantic:
                # Use semantic label if available for better readability
                display_name = field_def.get("semantic_label") or name
                important_fields.append(display_name)
            else:
                other_fields.append(name)

        return important_fields + other_fields
