"""
SemanticMetadataProfiler — heuristic-based semantic metadata generation.

Generates business-friendly names, descriptions, domain tags, query capabilities,
and suggested questions from technical schema metadata. Covers all source types:
PostgreSQL tables/views, MongoDB collections, documents (PDF/DOCX/TXT), and
structured datasets (CSV/Excel).

This is a heuristic-only implementation (no LLM calls). Uncertain results are
marked as low-confidence rather than fabricated.
"""

import re

import structlog

from app.schemas.discovery import (
    MongoCollectionInfo,
    MongoFieldInfo,
    PostgresColumnInfo,
    PostgresTableInfo,
    SemanticFieldInfo,
    SemanticProfile,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Domain keyword mappings for heuristic inference
# ---------------------------------------------------------------------------

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "finance": [
        "budget", "cost", "expense", "revenue", "invoice", "payment",
        "financial", "finance", "fiscal", "accounting", "profit", "loss",
        "variance", "forecast", "expenditure", "disbursement", "ledger",
        "billing", "receivable", "payable", "capital", "funding",
    ],
    "risk": [
        "risk", "threat", "vulnerability", "mitigation", "impact",
        "probability", "severity", "likelihood", "exposure", "hazard",
        "incident", "issue", "escalation",
    ],
    "schedule": [
        "schedule", "milestone", "deadline", "timeline", "duration",
        "start_date", "end_date", "due_date", "planned", "actual",
        "delay", "progress", "phase", "sprint", "iteration", "gantt",
    ],
    "resource": [
        "resource", "team", "member", "staff", "employee", "allocation",
        "capacity", "utilization", "headcount", "fte", "contractor",
        "personnel", "workforce", "role", "assignment",
    ],
    "quality": [
        "quality", "defect", "bug", "test", "review", "audit",
        "compliance", "standard", "metric", "kpi", "sla", "benchmark",
    ],
    "project": [
        "project", "program", "portfolio", "initiative", "workstream",
        "deliverable", "scope", "requirement", "objective", "goal",
    ],
    "jira": [
        "jira", "issue", "ticket", "story", "epic", "task", "subtask",
        "sprint", "backlog", "kanban", "assignee", "reporter", "priority",
    ],
    "document": [
        "document", "report", "meeting", "minutes", "note", "memo",
        "correspondence", "communication", "presentation", "template",
    ],
    "procurement": [
        "procurement", "vendor", "supplier", "contract", "purchase",
        "order", "tender", "bid", "rfp", "rfi",
    ],
    "change_management": [
        "change", "request", "approval", "workflow", "transition",
        "transformation", "migration", "adoption",
    ],
}

# Suggested questions templates per domain
DOMAIN_QUESTIONS: dict[str, list[str]] = {
    "finance": [
        "What is the current budget status?",
        "What are the top cost variances?",
        "How does actual spending compare to forecast?",
    ],
    "risk": [
        "What are the highest severity risks?",
        "Which risks are unmitigated?",
        "What is the overall risk exposure?",
    ],
    "schedule": [
        "What milestones are at risk of delay?",
        "What is the current schedule variance?",
        "Which tasks are behind schedule?",
    ],
    "resource": [
        "What is the current resource utilization?",
        "Which teams are over-allocated?",
        "What is the staffing plan status?",
    ],
    "quality": [
        "What are the open defect trends?",
        "How are quality metrics tracking?",
        "Which areas have compliance gaps?",
    ],
    "project": [
        "What is the overall project status?",
        "Which deliverables are in progress?",
        "What are the key project metrics?",
    ],
    "jira": [
        "What are the unresolved issues?",
        "How is the current sprint progressing?",
        "What are the blockers?",
    ],
    "document": [
        "What decisions were made in recent meetings?",
        "What are the key findings from the latest report?",
        "What action items are pending?",
    ],
    "procurement": [
        "What contracts are expiring soon?",
        "What is the procurement pipeline status?",
        "Which vendors need performance review?",
    ],
    "change_management": [
        "What change requests are pending approval?",
        "What is the adoption progress?",
        "Which changes have the highest impact?",
    ],
}

# Patterns for project-related field identification
PROJECT_FIELD_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^project[_\-]?id$", re.IGNORECASE),
    re.compile(r"^project[_\-]?code$", re.IGNORECASE),
    re.compile(r"^project[_\-]?key$", re.IGNORECASE),
    re.compile(r"^project[_\-]?name$", re.IGNORECASE),
    re.compile(r"^proj[_\-]?id$", re.IGNORECASE),
    re.compile(r"^prj[_\-]?id$", re.IGNORECASE),
    re.compile(r"^prj[_\-]?cd$", re.IGNORECASE),
]

# Document type to domain inference
DOCUMENT_TYPE_DOMAINS: dict[str, list[str]] = {
    "pdf": ["document"],
    "docx": ["document"],
    "txt": ["document"],
    "csv": [],
    "xlsx": [],
    "xls": [],
    "json": [],
}


class SemanticMetadataProfiler:
    """Generates semantic understanding from technical metadata.

    Produces business-friendly names, descriptions, domain tags,
    query capabilities, and suggested questions for each discovered object.

    Semantic inference is heuristic-based (no LLM calls). Uncertain results
    are marked as low-confidence rather than fabricated.
    """

    def profile_table(
        self, table_info: PostgresTableInfo, source_name: str
    ) -> SemanticProfile:
        """Generate semantic profile for a PostgreSQL table or view.

        Args:
            table_info: Technical metadata for the table/view.
            source_name: Human-readable name of the data source.

        Returns:
            SemanticProfile with heuristic-derived semantic metadata.
        """
        field_names = [col.name for col in table_info.columns]
        object_name = table_info.table_name

        semantic_name = self._derive_semantic_name(object_name)
        domain_tags = self._infer_domain_tags(object_name, field_names)
        confidence = self._determine_confidence(domain_tags)
        description = self._generate_table_description(
            semantic_name, field_names, table_info.table_type, source_name
        )
        query_capabilities = self._derive_query_capabilities(field_names)
        suggested_questions = self._generate_suggested_questions(domain_tags)
        important_fields = self._identify_important_fields(table_info.columns)
        project_fields = self.identify_project_fields(field_names)

        profile = SemanticProfile(
            semantic_name=semantic_name,
            description=description,
            domain_tags=domain_tags,
            important_fields=important_fields,
            query_capabilities=query_capabilities,
            suggested_questions=suggested_questions,
            confidence=confidence,
            project_fields=project_fields,
        )

        logger.debug(
            "table_profiled",
            table_name=object_name,
            source_name=source_name,
            domain_tags=domain_tags,
            confidence=confidence,
        )

        return profile

    def profile_collection(
        self, collection_info: MongoCollectionInfo, source_name: str
    ) -> SemanticProfile:
        """Generate semantic profile for a MongoDB collection.

        Args:
            collection_info: Technical metadata for the collection.
            source_name: Human-readable name of the data source.

        Returns:
            SemanticProfile with heuristic-derived semantic metadata.
        """
        field_names = [f.name for f in collection_info.inferred_fields]
        object_name = collection_info.collection_name

        semantic_name = self._derive_semantic_name(object_name)
        domain_tags = self._infer_domain_tags(object_name, field_names)
        confidence = self._determine_confidence(domain_tags)
        description = self._generate_collection_description(
            semantic_name, field_names, source_name,
            collection_info.document_count_estimate,
        )
        query_capabilities = self._derive_query_capabilities(field_names)
        suggested_questions = self._generate_suggested_questions(domain_tags)
        important_fields = self._identify_important_fields_from_mongo(
            collection_info.inferred_fields
        )
        project_fields = self.identify_project_fields(field_names)

        profile = SemanticProfile(
            semantic_name=semantic_name,
            description=description,
            domain_tags=domain_tags,
            important_fields=important_fields,
            query_capabilities=query_capabilities,
            suggested_questions=suggested_questions,
            confidence=confidence,
            project_fields=project_fields,
        )

        logger.debug(
            "collection_profiled",
            collection_name=object_name,
            source_name=source_name,
            domain_tags=domain_tags,
            confidence=confidence,
        )

        return profile

    def profile_document(
        self, file_name: str, document_type: str, metadata: dict
    ) -> SemanticProfile:
        """Generate semantic profile from Phase 4 ingestion metadata for documents.

        Reuses existing metadata extracted during document ingestion (page count,
        sections, content summary) — does NOT re-parse the document.

        Args:
            file_name: Original file name (e.g., "Q3_Risk_Report.pdf").
            document_type: File type extension (pdf, docx, txt).
            metadata: Metadata dict from Phase 4 ingestion (may include
                      page_count, sections, title, author, keywords, etc.).

        Returns:
            SemanticProfile for the document.
        """
        name_without_ext = self._strip_extension(file_name)
        semantic_name = self._derive_semantic_name(name_without_ext)

        # Combine file name tokens with any metadata keywords for domain inference
        name_tokens = self._tokenize_name(name_without_ext)
        metadata_keywords = metadata.get("keywords", [])
        if isinstance(metadata_keywords, str):
            metadata_keywords = [k.strip() for k in metadata_keywords.split(",")]
        all_tokens = name_tokens + metadata_keywords

        domain_tags = self._infer_domain_tags_from_tokens(all_tokens)
        # Add base document domain from type if no other domains found
        type_domains = DOCUMENT_TYPE_DOMAINS.get(document_type.lower(), [])
        if not domain_tags and type_domains:
            domain_tags = type_domains

        confidence = self._determine_confidence(domain_tags)
        description = self._generate_document_description(
            semantic_name, document_type, metadata
        )
        query_capabilities = self._derive_document_capabilities(metadata)
        suggested_questions = self._generate_suggested_questions(domain_tags)

        profile = SemanticProfile(
            semantic_name=semantic_name,
            description=description,
            domain_tags=domain_tags,
            important_fields=[],
            query_capabilities=query_capabilities,
            suggested_questions=suggested_questions,
            confidence=confidence,
            project_fields=[],
        )

        logger.debug(
            "document_profiled",
            file_name=file_name,
            document_type=document_type,
            domain_tags=domain_tags,
            confidence=confidence,
        )

        return profile

    def profile_dataset(
        self, file_name: str, columns: list[str], row_count: int | None = None
    ) -> SemanticProfile:
        """Generate semantic profile for structured data (CSV, Excel sheets).

        Args:
            file_name: Original file name (e.g., "budget_tracker.xlsx").
            columns: List of column/header names in the dataset.
            row_count: Optional estimated row count.

        Returns:
            SemanticProfile for the structured dataset.
        """
        name_without_ext = self._strip_extension(file_name)
        semantic_name = self._derive_semantic_name(name_without_ext)

        # Use both file name and column names for domain inference
        name_tokens = self._tokenize_name(name_without_ext)
        all_tokens = name_tokens + [c.lower() for c in columns]
        domain_tags = self._infer_domain_tags_from_tokens(all_tokens)
        confidence = self._determine_confidence(domain_tags)

        description = self._generate_dataset_description(
            semantic_name, columns, row_count
        )
        query_capabilities = self._derive_query_capabilities(columns)
        suggested_questions = self._generate_suggested_questions(domain_tags)
        project_fields = self.identify_project_fields(columns)

        # Build field info for columns (limit to top 20)
        important_fields = [
            SemanticFieldInfo(
                technical_name=col,
                semantic_label=self._humanize_field_name(col),
                description=f"Column: {self._humanize_field_name(col)}",
                is_identifier=self._is_identifier_field(col),
                is_project_field=col in project_fields,
            )
            for col in columns[:20]
        ]

        profile = SemanticProfile(
            semantic_name=semantic_name,
            description=description,
            domain_tags=domain_tags,
            important_fields=important_fields,
            query_capabilities=query_capabilities,
            suggested_questions=suggested_questions,
            confidence=confidence,
            project_fields=project_fields,
        )

        logger.debug(
            "dataset_profiled",
            file_name=file_name,
            column_count=len(columns),
            domain_tags=domain_tags,
            confidence=confidence,
        )

        return profile

    def identify_project_fields(self, field_names: list[str]) -> list[str]:
        """Identify fields likely representing project relationships.

        Matches patterns: project_id, project_code, project_key,
        project_name, proj_id, prj_id, prj_cd.

        Args:
            field_names: List of field/column names to check.

        Returns:
            List of field names that match project field patterns.
        """
        matches: list[str] = []
        for name in field_names:
            for pattern in PROJECT_FIELD_PATTERNS:
                if pattern.match(name):
                    matches.append(name)
                    break
        return matches

    # -------------------------------------------------------------------------
    # Private helpers — name derivation
    # -------------------------------------------------------------------------

    def _derive_semantic_name(self, raw_name: str) -> str:
        """Convert a technical name to a human-friendly title.

        Examples:
            "project_finance" → "Project Finance"
            "jira_issues" → "JIRA Issues"
            "risk_register" → "Risk Register"
            "Q3_Risk_Report" → "Q3 Risk Report"
        """
        acronyms = {"jira", "sql", "api", "csv", "pdf", "rag", "kpi", "sla", "sdlc"}

        # Split on underscores, hyphens, and spaces
        parts = re.split(r"[_\-\s]+", raw_name)
        titled_parts: list[str] = []

        for part in parts:
            if not part:
                continue
            if part.lower() in acronyms:
                titled_parts.append(part.upper())
            else:
                titled_parts.append(part.capitalize())

        return " ".join(titled_parts) if titled_parts else raw_name

    def _strip_extension(self, file_name: str) -> str:
        """Remove file extension from a filename."""
        name = file_name
        for ext in [".xlsx", ".xls", ".csv", ".pdf", ".docx", ".txt", ".json"]:
            if name.lower().endswith(ext):
                name = name[: -len(ext)]
                break
        return name

    def _tokenize_name(self, name: str) -> list[str]:
        """Split a name into lowercase tokens for keyword matching."""
        parts = re.split(r"[_\-\s]+", name)
        return [p.lower() for p in parts if p]

    def _humanize_field_name(self, field_name: str) -> str:
        """Convert a technical field name to a readable label.

        Examples:
            "actl_exp" → "Actual Expense"
            "budget_variance" → "Budget Variance"
            "project_id" → "Project ID"
        """
        abbreviations: dict[str, str] = {
            "actl": "actual",
            "exp": "expense",
            "amt": "amount",
            "qty": "quantity",
            "num": "number",
            "dt": "date",
            "desc": "description",
            "prj": "project",
            "proj": "project",
            "cd": "code",
            "nm": "name",
            "sts": "status",
            "flg": "flag",
            "cnt": "count",
            "pct": "percent",
            "avg": "average",
            "tot": "total",
            "yr": "year",
            "mo": "month",
            "wk": "week",
            "mgr": "manager",
            "dept": "department",
            "org": "organization",
            "alloc": "allocation",
            "util": "utilization",
            "var": "variance",
        }

        id_terms = {"id", "uuid", "pk"}

        parts = re.split(r"[_\-]+", field_name.lower())
        expanded: list[str] = []

        for part in parts:
            if part in id_terms:
                expanded.append("ID")
            elif part in abbreviations:
                expanded.append(abbreviations[part].capitalize())
            else:
                expanded.append(part.capitalize())

        return " ".join(expanded)

    # -------------------------------------------------------------------------
    # Private helpers — domain inference
    # -------------------------------------------------------------------------

    def _infer_domain_tags(
        self, object_name: str, field_names: list[str]
    ) -> list[str]:
        """Infer domain tags from object name and field names."""
        all_tokens = self._tokenize_name(object_name) + [
            f.lower() for f in field_names
        ]
        return self._infer_domain_tags_from_tokens(all_tokens)

    def _infer_domain_tags_from_tokens(self, tokens: list[str]) -> list[str]:
        """Infer domain tags from a list of lowercase tokens."""
        domain_scores: dict[str, int] = {}

        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = 0
            for token in tokens:
                for keyword in keywords:
                    if keyword in token or token in keyword:
                        score += 1
                        break
            if score > 0:
                domain_scores[domain] = score

        if not domain_scores:
            return []

        # Return domains sorted by relevance score, top 3 max
        sorted_domains = sorted(
            domain_scores.items(), key=lambda x: x[1], reverse=True
        )
        return [d[0] for d in sorted_domains[:3]]

    def _determine_confidence(self, domain_tags: list[str]) -> str:
        """Determine confidence level based on domain inference clarity.

        Returns:
            "high" if strong domain signal, "medium" for heuristic matches,
            "low" for unknown/ambiguous domains.
        """
        if not domain_tags:
            return "low"
        if len(domain_tags) == 1 and domain_tags[0] != "document":
            return "high"
        return "medium"

    # -------------------------------------------------------------------------
    # Private helpers — description generation
    # -------------------------------------------------------------------------

    def _generate_table_description(
        self,
        semantic_name: str,
        field_names: list[str],
        object_type: str,
        source_name: str,
    ) -> str:
        """Generate a business description for a PostgreSQL table/view."""
        field_count = len(field_names)
        notable_fields = ", ".join(field_names[:5])
        suffix = f" and {field_count - 5} more" if field_count > 5 else ""

        return (
            f"{semantic_name} ({object_type}) from {source_name}. "
            f"Contains {field_count} fields including {notable_fields}{suffix}."
        )

    def _generate_collection_description(
        self,
        semantic_name: str,
        field_names: list[str],
        source_name: str,
        doc_count: int | None,
    ) -> str:
        """Generate a business description for a MongoDB collection."""
        field_count = len(field_names)
        notable_fields = ", ".join(field_names[:5])
        suffix = f" and {field_count - 5} more" if field_count > 5 else ""

        count_str = f" with ~{doc_count} documents" if doc_count else ""

        return (
            f"{semantic_name} (collection) from {source_name}{count_str}. "
            f"Contains {field_count} fields including {notable_fields}{suffix}."
        )

    def _generate_document_description(
        self, semantic_name: str, document_type: str, metadata: dict
    ) -> str:
        """Generate a description for a document source."""
        parts: list[str] = [f"{semantic_name} ({document_type.upper()} document)"]

        page_count = metadata.get("page_count")
        if page_count:
            parts.append(f"{page_count} pages")

        title = metadata.get("title")
        if title and title != semantic_name:
            parts.append(f'titled "{title}"')

        sections = metadata.get("sections")
        if sections and isinstance(sections, list):
            section_str = ", ".join(sections[:3])
            parts.append(f"sections: {section_str}")

        return ". ".join(parts) + "."

    def _generate_dataset_description(
        self, semantic_name: str, columns: list[str], row_count: int | None
    ) -> str:
        """Generate a description for a structured dataset (CSV/Excel)."""
        col_count = len(columns)
        notable = ", ".join(columns[:5])
        suffix = f" and {col_count - 5} more" if col_count > 5 else ""

        row_str = f" with ~{row_count} rows" if row_count else ""

        return (
            f"{semantic_name} (structured dataset){row_str}. "
            f"Contains {col_count} columns including {notable}{suffix}."
        )

    # -------------------------------------------------------------------------
    # Private helpers — capabilities and questions
    # -------------------------------------------------------------------------

    def _derive_query_capabilities(self, field_names: list[str]) -> list[str]:
        """Derive query capabilities from field/column names.

        Returns field names that represent queryable data dimensions.
        Filters out generic identifiers and metadata fields.
        """
        skip_patterns = {"id", "uuid", "created_at", "updated_at", "_id"}
        capabilities: list[str] = []

        for name in field_names:
            lower = name.lower()
            if lower in skip_patterns:
                continue
            if lower.endswith("_id") and lower != "project_id":
                continue
            capabilities.append(name)

        # Limit to most relevant 10
        return capabilities[:10]

    def _derive_document_capabilities(self, metadata: dict) -> list[str]:
        """Derive query capabilities from document metadata."""
        capabilities: list[str] = []

        if metadata.get("sections"):
            capabilities.append("section_search")
        if metadata.get("page_count"):
            capabilities.append("page_reference")
        if metadata.get("title"):
            capabilities.append("title_search")
        if metadata.get("keywords"):
            capabilities.append("keyword_search")

        # Always support full-text search for documents
        capabilities.append("full_text_search")
        return capabilities

    def _generate_suggested_questions(self, domain_tags: list[str]) -> list[str]:
        """Generate 2-3 example questions based on detected domains."""
        questions: list[str] = []

        for tag in domain_tags[:2]:
            tag_questions = DOMAIN_QUESTIONS.get(tag, [])
            for q in tag_questions[:2]:
                if len(questions) >= 3:
                    break
                questions.append(q)
            if len(questions) >= 3:
                break

        if not questions:
            questions.append("What data is available in this source?")

        return questions

    # -------------------------------------------------------------------------
    # Private helpers — field classification
    # -------------------------------------------------------------------------

    def _identify_important_fields(
        self, columns: list[PostgresColumnInfo]
    ) -> list[SemanticFieldInfo]:
        """Identify and annotate important fields from PostgreSQL columns.

        Args:
            columns: List of PostgresColumnInfo from table discovery.

        Returns:
            List of SemanticFieldInfo for notable columns (limited to 20).
        """
        important: list[SemanticFieldInfo] = []
        for col in columns[:20]:
            is_project = any(p.match(col.name) for p in PROJECT_FIELD_PATTERNS)
            important.append(
                SemanticFieldInfo(
                    technical_name=col.name,
                    semantic_label=self._humanize_field_name(col.name),
                    description=f"{col.data_type}, {'nullable' if col.nullable else 'not null'}",
                    is_identifier=col.is_primary_key or self._is_identifier_field(col.name),
                    is_project_field=is_project,
                )
            )
        return important

    def _identify_important_fields_from_mongo(
        self, fields: list[MongoFieldInfo]
    ) -> list[SemanticFieldInfo]:
        """Identify and annotate important fields from MongoDB field info.

        Args:
            fields: List of MongoFieldInfo from collection discovery.

        Returns:
            List of SemanticFieldInfo for notable fields (limited to 20).
        """
        important: list[SemanticFieldInfo] = []
        for f in fields[:20]:
            is_project = any(p.match(f.name) for p in PROJECT_FIELD_PATTERNS)
            important.append(
                SemanticFieldInfo(
                    technical_name=f.name,
                    semantic_label=self._humanize_field_name(f.name),
                    description=f"{f.inferred_type}, path: {f.field_path}",
                    is_identifier=self._is_identifier_field(f.name),
                    is_project_field=is_project,
                )
            )
        return important

    def _is_identifier_field(self, field_name: str) -> bool:
        """Check if a field name looks like an identifier."""
        lower = field_name.lower()
        return (
            lower.endswith("_id")
            or lower.endswith("_uuid")
            or lower == "id"
            or lower == "_id"
            or lower.endswith("_key")
            or lower.endswith("_code")
        )

    # -------------------------------------------------------------------------
    # Backward-compatible async adapters
    # -------------------------------------------------------------------------
    # NOTE: These exist to support existing callers (discovery_engine.py,
    # document_catalog_integration.py) that use `await profiler.profile_*(...)`.
    # Tasks 3.2 and 3.3 will update those callers to use the sync interface.
    # These adapters can be removed once all callers are migrated.

    async def async_profile_table(
        self, table_info: PostgresTableInfo, source_name: str
    ) -> SemanticProfile:
        """Async wrapper for profile_table — for backward compatibility."""
        return self.profile_table(table_info, source_name)

    async def async_profile_collection(
        self, collection_info: MongoCollectionInfo, source_name: str
    ) -> SemanticProfile:
        """Async wrapper for profile_collection — for backward compatibility."""
        return self.profile_collection(collection_info, source_name)

    async def async_profile_document(
        self, file_name: str, document_type: str, metadata: dict
    ) -> SemanticProfile:
        """Async wrapper for profile_document — for backward compatibility."""
        return self.profile_document(file_name, document_type, metadata)

    async def async_profile_dataset(
        self, file_name: str, columns: list[str], row_count: int | None = None
    ) -> SemanticProfile:
        """Async wrapper for profile_dataset — for backward compatibility."""
        return self.profile_dataset(file_name, columns, row_count)
