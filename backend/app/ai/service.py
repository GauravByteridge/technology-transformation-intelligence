"""
AI Service — Orchestration entry point.

The AIService is the top-level orchestrator for AI query execution.
It coordinates the flow: load prompt → invoke agent with tools → build response.

Invocation Flow:
    API → AIService → StrandsAgentWrapper → Strands Agent → Tools → IngestionInterface

Phase 5 Update:
- The service now supports both the legacy AIAgent (Phase 0) and the new
  StrandsAgentWrapper (Phase 5). When a StrandsAgentWrapper is provided,
  it takes precedence for query execution.

Phase 8 Update:
- When a CrossSourceOrchestrator is injected (real mode with catalog awareness),
  execute_query delegates to the orchestrator for catalog context injection,
  evidence building, lineage recording, and failure isolation.
- Demo mode (no orchestrator) continues using existing behavior unchanged.

Security Invariants:
- AIService does NOT receive or pass database credentials to the agent.
- AIService does NOT import database drivers.
- All data access flows through registered tools → domain services.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.ai.agent import AIAgent, AgentResponse, ToolResult
from app.ai.prompt_manager import PromptManager
from app.ai.providers.protocol import TextGenerationProvider
from app.ai.response import strip_markup
from app.ai.tools.registry import ToolRegistry
from app.ai.trace import QueryTrace, ToolInvocationTrace, sanitize_log_value
from app.schemas.ai import AIResponse

if TYPE_CHECKING:
    from app.ai.cross_source_orchestrator import CrossSourceOrchestrator
    from app.ai.strands_agent import StrandsAgentWrapper

logger = logging.getLogger(__name__)


class AIService:
    """Orchestration entry point for AI query execution.

    Responsibilities:
    - Accept queries from the API layer
    - Configure and invoke the AI agent with appropriate tools
    - Transform agent responses into the structured AIResponse contract
    - Handle partial failures gracefully
    - Record tracing information for observability

    The service is injected with its dependencies (provider, tool_registry,
    prompt_manager) and never instantiates them internally.

    Phase 5: When a StrandsAgentWrapper is provided, the service delegates to
    the Strands Agent for LLM-driven tool selection and reasoning. The legacy
    AIAgent remains as a fallback.

    Phase 8: When a CrossSourceOrchestrator is provided (real mode), the service
    delegates to the orchestrator for catalog-aware, evidence-backed, lineage-traced
    query execution. Demo mode (no orchestrator) continues using existing behavior.
    """

    def __init__(
        self,
        provider: TextGenerationProvider,
        tool_registry: ToolRegistry,
        prompt_manager: PromptManager | None = None,
        strands_agent: "StrandsAgentWrapper | None" = None,
        cross_source_orchestrator: "CrossSourceOrchestrator | None" = None,
    ) -> None:
        """Initialize the AI service.

        Args:
            provider: Text generation provider for LLM calls.
            tool_registry: Registry of domain-scoped AI tools.
            prompt_manager: Prompt template manager for loading versioned prompts.
                Defaults to None; when provided, system prompts are loaded from
                the prompts directory with version tracking.
            strands_agent: Optional Strands Agent wrapper for Phase 5 intelligent
                tool selection. When provided, takes precedence over the legacy agent.
            cross_source_orchestrator: Optional Phase 8 orchestrator for catalog-aware
                cross-source execution with evidence and lineage. When provided
                (real mode), takes precedence over direct Strands invocation.
        """
        self._provider = provider
        self._tool_registry = tool_registry
        self._prompt_manager = prompt_manager
        self._strands_agent = strands_agent
        self._cross_source_orchestrator = cross_source_orchestrator
        self._agent = AIAgent(provider=provider, tool_registry=tool_registry)
        self._last_trace: QueryTrace | None = None

    async def execute_query(
        self,
        question: str,
        project_id: UUID,
        query_id: UUID,
        conversation_id: UUID,
    ) -> AIResponse:
        """Execute an AI query through the full orchestration pipeline.

        Flow (Phase 8 — real mode with CrossSourceOrchestrator):
        1. Delegate to orchestrator: catalog context → Strands → failure isolation → evidence → lineage
        2. Build enhanced AIResponse from CrossSourceResult

        Flow (demo mode — no orchestrator):
        1. Log query start with tracing identifiers
        2. Invoke agent with registered tools and project context
        3. Transform agent response into structured AIResponse
        4. Record trace information

        Args:
            question: The user's natural-language question.
            project_id: Project context for scoping data retrieval.
            query_id: Unique identifier for this specific query execution.
            conversation_id: Conversation this query belongs to.

        Returns:
            Structured AIResponse matching the platform's response contract.
        """
        start_time = time.perf_counter()

        logger.info(
            "ai_query_started",
            extra={
                "query_id": str(query_id),
                "conversation_id": str(conversation_id),
                "project_id": str(project_id),
                "question_length": len(question),
                "mode": "real" if self._cross_source_orchestrator else "demo",
            },
        )

        try:
            # Phase 8: Use CrossSourceOrchestrator when available (real mode)
            if self._cross_source_orchestrator is not None:
                return await self._execute_with_orchestrator(
                    question=question,
                    project_id=project_id,
                    query_id=query_id,
                    conversation_id=conversation_id,
                    start_time=start_time,
                )

            # Demo mode / legacy path: direct Strands or Phase 0 agent
            # Phase 5: Use Strands Agent when available for LLM-driven tool selection
            if self._strands_agent is not None:
                agent_response = await self._strands_agent.invoke(
                    question=question,
                    project_id=project_id,
                    query_id=query_id,
                )
            else:
                # Legacy Phase 0 agent — invokes all tools
                agent_response = await self._agent.invoke(
                    question=question,
                    project_id=project_id,
                    query_id=query_id,
                )

            ai_response = self._build_response(
                agent_response=agent_response,
                query_id=query_id,
                conversation_id=conversation_id,
            )

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Build and store the structured trace record
            trace = self._build_trace(
                query_id=query_id,
                conversation_id=conversation_id,
                question=question,
                project_id=project_id,
                agent_response=agent_response,
                duration_ms=duration_ms,
            )
            self._last_trace = trace

            logger.info(
                "ai_query_completed",
                extra={
                    "query_id": str(query_id),
                    "conversation_id": str(conversation_id),
                    "duration_ms": duration_ms,
                    "is_partial": ai_response.is_partial,
                    "sources_count": len(ai_response.sources),
                    "response_type": ai_response.response_type,
                    "provider": trace.provider,
                    "model": trace.model,
                    "execution_status": "success",
                    "mode": "demo",
                },
            )

            return ai_response

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Sanitize the error message to prevent credential leakage
            safe_error = sanitize_log_value(str(exc))

            logger.error(
                "ai_query_failed",
                extra={
                    "query_id": str(query_id),
                    "conversation_id": str(conversation_id),
                    "duration_ms": duration_ms,
                    "error": safe_error,
                    "error_type": type(exc).__name__,
                    "execution_status": "failed",
                },
                exc_info=True,
            )
            # Return a structured failure response rather than raising
            return AIResponse(
                answer=(
                    "I encountered an error while processing your question. "
                    "Please try again or rephrase your query."
                ),
                response_type="text",
                sources=[],
                evidence=[],
                query_id=query_id,
                conversation_id=conversation_id,
                is_partial=True,
                failed_sources=[{"source": "system", "error": "Internal processing error"}],
            )

    async def _execute_with_orchestrator(
        self,
        question: str,
        project_id: UUID,
        query_id: UUID,
        conversation_id: UUID,
        start_time: float,
    ) -> AIResponse:
        """Execute query via CrossSourceOrchestrator (real mode).

        Delegates to the orchestrator for catalog-aware execution and builds
        the enhanced AIResponse with evidence, lineage, and source information.

        Args:
            question: The user's natural-language question.
            project_id: Project context for scoping data retrieval.
            query_id: Unique query identifier.
            conversation_id: Conversation this query belongs to.
            start_time: Performance counter start for duration tracking.

        Returns:
            Enhanced AIResponse with Phase 8 fields populated.
        """
        from app.ai.cross_source_orchestrator import CrossSourceResult

        result: CrossSourceResult = (
            await self._cross_source_orchestrator.execute_cross_source_query(
                question=question,
                project_id=project_id,
                query_id=query_id,
            )
        )

        # Build the enhanced AIResponse from CrossSourceResult
        ai_response = self._build_response_from_cross_source(
            result=result,
            query_id=query_id,
            conversation_id=conversation_id,
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Build trace from the orchestrator's tool results for observability
        agent_response = AgentResponse(
            answer=result.answer,
            model=result.model,
            tool_results=result.tool_results,
            is_partial=result.is_partial,
        )
        trace = self._build_trace(
            query_id=query_id,
            conversation_id=conversation_id,
            question=question,
            project_id=project_id,
            agent_response=agent_response,
            duration_ms=duration_ms,
        )
        self._last_trace = trace

        logger.info(
            "ai_query_completed",
            extra={
                "query_id": str(query_id),
                "conversation_id": str(conversation_id),
                "duration_ms": duration_ms,
                "is_partial": ai_response.is_partial,
                "sources_count": len(ai_response.sources),
                "evidence_count": len(ai_response.evidence),
                "response_type": ai_response.response_type,
                "provider": trace.provider,
                "model": trace.model,
                "execution_status": "success",
                "mode": "real",
            },
        )

        return ai_response

    def _build_response(
        self,
        agent_response: AgentResponse,
        query_id: UUID,
        conversation_id: UUID,
    ) -> AIResponse:
        """Transform an AgentResponse into the structured AIResponse contract.

        Maps tool results into sources and evidence arrays with meaningful
        labels (not internal tool names or function signatures). Produces
        typed evidence items with data.type for frontend classifyEvidenceType.

        Used in demo mode (no orchestrator). Real mode uses
        _build_response_from_cross_source instead.

        Args:
            agent_response: The raw response from the AI agent.
            query_id: Query identifier for tracing.
            conversation_id: Conversation identifier.

        Returns:
            Structured AIResponse ready for the API layer.
        """
        sources: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        failed_sources: list[dict[str, Any]] = []

        for result in agent_response.tool_results:
            try:
                if result.success:
                    data = result.data if isinstance(result.data, dict) else {"raw": result.data}

                    # Build a descriptive source name from tool metadata
                    source_name = result.source_label or "Unknown"
                    source_meta = data.get("source_metadata", {})
                    if isinstance(source_meta, dict) and source_meta.get("source_name"):
                        obj_name = source_meta.get("object_name", "")
                        source_name = f"{source_meta['source_name']} — {obj_name}" if obj_name else source_meta["source_name"]

                    # Get record count from various possible fields
                    records = (
                        data.get("row_count")
                        or data.get("record_count")
                        or data.get("result_count")
                        or data.get("total_count")
                        or data.get("dataset_count")
                        or data.get("total_sources")
                        or 0
                    )

                    source_entry = {
                        "name": source_name,
                        "type": data.get("source_type", source_meta.get("source_type", "unknown") if isinstance(source_meta, dict) else "unknown"),
                        "records_returned": records,
                    }

                    sources.append(source_entry)

                    tool_evidence = self._extract_typed_evidence(result)
                    evidence.extend(tool_evidence)
                else:
                    failed_sources.append({
                        "source": result.source_label or result.tool_name,
                        "error": sanitize_log_value(result.error) if result.error else "Unknown error",
                    })
            except Exception as e:
                logger.warning("tool_result_processing_skipped", extra={"error": str(e), "tool": result.tool_name})

        # Detect if we have tabular data suitable for visualization
        visualization_spec = self._detect_visualization(agent_response, sources)
        # If no tool data was chart-worthy, try parsing the answer's markdown table
        if not visualization_spec:
            visualization_spec = self._detect_visualization_from_answer(agent_response.answer)
        response_type = "chart" if visualization_spec else "text"

        # If visualization was generated from the answer's markdown table,
        # strip the table from the answer to avoid duplicate display
        answer_text = strip_markup(agent_response.answer)
        if visualization_spec and response_type == "chart":
            answer_text = self._strip_markdown_table(answer_text)

        return AIResponse(
            answer=answer_text,
            response_type=response_type,
            sources=sources,
            evidence=evidence,
            query_id=query_id,
            conversation_id=conversation_id,
            is_partial=agent_response.is_partial,
            failed_sources=failed_sources,
            visualization_spec=visualization_spec,
        )

    def _detect_visualization(self, agent_response: AgentResponse, sources: list[dict]) -> dict | None:
        """Detect if the response contains data suitable for chart visualization.

        Looks for tool results with multiple rows of structured data that could
        be meaningfully displayed as a bar/line/pie chart.
        """
        for result in agent_response.tool_results:
            if not result.success or not isinstance(result.data, dict):
                continue

            # Connected source queries with multiple rows
            rows = result.data.get("rows", [])
            columns = result.data.get("columns", [])

            if len(rows) >= 3 and len(columns) >= 2:
                x_col, y_cols, is_time_series = self._detect_chart_columns(rows, columns)
                if x_col and y_cols:
                    # Double-check: if x values look like dates, force line chart
                    if not is_time_series:
                        sample_x = [r.get(x_col, "") for r in rows[:3] if isinstance(r, dict)]
                        if any(self._looks_like_date(str(v)) for v in sample_x):
                            is_time_series = True
                    chart_type = "line" if is_time_series else "bar"
                    chart_data = []
                    for row in rows[:20]:
                        if isinstance(row, dict):
                            entry = {x_col: row.get(x_col, "")}
                            for yc in y_cols:
                                val = row.get(yc, 0)
                                entry[yc] = self._to_number(val)
                            chart_data.append(entry)

                    return {
                        "chart_type": chart_type,
                        "data": chart_data,
                        "xKey": x_col,
                        "yKey": y_cols[0],
                        "columns": columns,
                        "rows": rows[:20],
                    }

            # Dataset queries with records
            records = result.data.get("records", [])
            if isinstance(records, list) and len(records) >= 2 and records and isinstance(records[0], dict):
                keys = list(records[0].keys())
                x_col, y_cols, is_time_series = self._detect_chart_columns(records, keys)
                if x_col and y_cols:
                    chart_type = "line" if is_time_series else "bar"
                    chart_data = []
                    for rec in records[:20]:
                        entry = {x_col: rec.get(x_col, "")}
                        for yc in y_cols:
                            entry[yc] = self._to_number(rec.get(yc, 0))
                        chart_data.append(entry)
                    return {
                        "chart_type": chart_type,
                        "data": chart_data,
                        "xKey": x_col,
                        "yKey": y_cols[0],
                        "columns": keys,
                        "rows": records[:20],
                    }

        return None

    def _strip_markdown_table(self, text: str) -> str:
        """Remove markdown table lines from text to avoid duplicate display."""
        import re
        lines = text.split('\n')
        result = []
        in_table = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('|') and stripped.endswith('|'):
                in_table = True
                continue  # Skip table lines
            elif in_table and not stripped:
                in_table = False
                continue  # Skip blank line after table
            else:
                in_table = False
                result.append(line)
        return '\n'.join(result).strip()

    def _detect_visualization_from_answer(self, answer: str) -> dict | None:
        """Parse markdown tables from the AI answer and build a chart spec.

        Detects | col1 | col2 | format tables and identifies numeric columns.
        """
        import re

        lines = answer.split('\n')
        table_rows: list[list[str]] = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('|') and stripped.endswith('|'):
                # Skip separator rows
                if re.match(r'^\|[\s\-:|]+\|$', stripped):
                    continue
                cells = [c.strip() for c in stripped.split('|')[1:-1]]
                if cells:
                    table_rows.append(cells)
                    in_table = True
            elif in_table:
                break  # End of table

        if len(table_rows) < 4:  # Need header + at least 3 data rows
            return None

        headers = table_rows[0]
        data_rows = table_rows[1:]

        # Find X (text) and Y (numeric) columns
        x_idx = None
        y_indices = []

        for col_idx, header in enumerate(headers):
            # Check if this column's values are numeric
            numeric_count = 0
            for row in data_rows:
                if col_idx < len(row):
                    if self._is_numeric(row[col_idx]):
                        numeric_count += 1

            if numeric_count >= len(data_rows) * 0.6:  # 60% numeric
                y_indices.append(col_idx)
            elif x_idx is None:
                x_idx = col_idx

        if x_idx is None or not y_indices:
            return None

        # Build chart data
        chart_data = []
        for row in data_rows:
            if x_idx < len(row):
                entry = {headers[x_idx]: row[x_idx]}
                for yi in y_indices:
                    if yi < len(row):
                        entry[headers[yi]] = self._to_number(row[yi])
                chart_data.append(entry)

        if len(chart_data) < 2:
            return None

        # Detect if X column looks like dates → line chart, otherwise bar
        x_values = [entry.get(headers[x_idx], "") for entry in chart_data]
        is_time = any(self._looks_like_date(str(v)) for v in x_values[:3])
        chart_type = "line" if is_time else "bar"

        return {
            "chart_type": chart_type,
            "data": chart_data,
            "xKey": headers[x_idx],
            "yKey": headers[y_indices[0]],
            "columns": headers,
            "rows": [dict(zip(headers, row)) for row in data_rows],
        }

    def _detect_chart_columns(self, rows: list, columns: list) -> tuple[str | None, list[str]]:
        """Detect X (label) and Y (numeric) columns from data rows."""
        x_col = None
        y_cols = []
        is_time_series = False

        for col in columns:
            values = []
            for row in rows[:5]:
                if isinstance(row, dict):
                    values.append(row.get(col))

            # Skip columns with UUID-like or ObjectId-like values
            text_values = [v for v in values if isinstance(v, str)]
            if text_values and any(len(v) > 24 and '-' in v for v in text_values):
                continue  # Likely UUIDs/ObjectIDs — skip

            # Detect date columns (for time-series / line charts)
            if text_values and any(self._looks_like_date(v) for v in text_values):
                if not x_col:
                    x_col = col
                    is_time_series = True
                continue

            numeric_count = sum(1 for v in values if self._is_numeric(v))
            text_count = sum(1 for v in values if isinstance(v, str) and not self._is_numeric(v))

            if numeric_count > text_count and numeric_count >= 2:
                # Only consider columns with meaningful numeric values (not just row IDs)
                numeric_vals = [self._to_number(v) for v in values if self._is_numeric(v)]
                if numeric_vals and max(numeric_vals) > 10:  # Skip trivial counts like 1,2,3
                    y_cols.append(col)
            elif text_count > 0 and not x_col:
                # Only use short readable text as X labels
                if text_values and all(len(v) < 30 for v in text_values):
                    x_col = col

        return x_col, y_cols, is_time_series

    @staticmethod
    def _looks_like_date(val: str) -> bool:
        """Check if a string looks like a date."""
        import re
        # Normalize unicode hyphens/dashes to regular hyphen
        normalized = val.strip().replace('\u2013', '-').replace('\u2014', '-').replace('\u00a0', ' ')
        if re.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', normalized):
            return True
        if re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', normalized):
            return True
        date_keywords = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        if any(kw in val.lower() for kw in date_keywords):
            return True
        return False

    @staticmethod
    def _is_numeric(val) -> bool:
        """Check if a value is numeric (including string numbers)."""
        if isinstance(val, (int, float)):
            return True
        if isinstance(val, str):
            import re
            # Normalize unicode and check for date patterns
            normalized = val.strip().replace('\u2013', '-').replace('\u2014', '-').replace('\u00a0', ' ')
            if re.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', normalized):
                return False
            cleaned = val.replace(",", "").replace("$", "").replace("%", "").replace("+", "").strip()
            # Only strip leading minus for negative numbers
            if cleaned.startswith("-"):
                cleaned = cleaned[1:]
            try:
                float(cleaned)
                return True
            except (ValueError, TypeError):
                return False
        return False

    @staticmethod
    def _to_number(val) -> float:
        """Convert a value to a number for charting."""
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            cleaned = val.replace(",", "").replace("$", "").replace("%", "").replace("+", "").strip()
            try:
                return float(cleaned)
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    def _extract_typed_evidence(self, result: ToolResult) -> list[dict[str, Any]]:
        """Extract typed evidence items from a successful tool result.

        Maps raw tool result data into evidence items with a data.type field
        suitable for the frontend EvidencePanel's classifyEvidenceType logic.

        Supported types: "document", "dataset", "excel"

        Args:
            result: A successful ToolResult with structured data.

        Returns:
            List of evidence dicts with {claim, source, data} structure.
        """
        evidence_items: list[dict[str, Any]] = []

        # Safety: if data is not a dict, skip evidence extraction
        if not isinstance(result.data, dict):
            return evidence_items

        if result.tool_name == "search_documents":
            evidence_items.extend(self._build_document_evidence(result))
        elif result.tool_name == "query_dataset":
            evidence_items.extend(self._build_dataset_evidence(result))
        elif result.tool_name == "get_evidence":
            evidence_items.extend(self._build_detailed_evidence(result))
        elif result.tool_name in ("list_available_datasets", "get_dataset_metadata"):
            pass
        else:
            tool_evidence = result.data.get("evidence", [])
            for item in tool_evidence:
                if isinstance(item, dict):
                    evidence_items.append({
                        "claim": item.get("claim", ""),
                        "source": result.source_label,
                        "data": item.get("data"),
                    })

        return evidence_items

    def _build_document_evidence(self, result: ToolResult) -> list[dict[str, Any]]:
        """Build evidence items from search_documents results."""
        items: list[dict[str, Any]] = []
        if not isinstance(result.data, dict):
            return items
        search_results = result.data.get("results", [])

        for doc_result in search_results:
            if not isinstance(doc_result, dict):
                continue

            file_name = doc_result.get("file_name", "")
            excerpt = doc_result.get("excerpt", "")
            section = doc_result.get("section", doc_result.get("page_number", ""))
            score = doc_result.get("similarity_score", doc_result.get("score", None))

            # Build a claim from the excerpt
            claim = excerpt[:150] if excerpt else f"Evidence from {file_name}"

            items.append({
                "claim": claim,
                "source": result.source_label,
                "data": {
                    "type": "document",
                    "file_name": file_name,
                    "page_or_section": str(section) if section else None,
                    "text_excerpt": excerpt,
                    "relevance_score": score,
                },
            })

        return items

    def _build_dataset_evidence(self, result: ToolResult) -> list[dict[str, Any]]:
        """Build evidence items from query_dataset results."""
        items: list[dict[str, Any]] = []
        if not isinstance(result.data, dict):
            return items
        records = result.data.get("records", [])
        aggregations = result.data.get("aggregations", {})
        source_file = result.data.get("source_file", "")
        dataset_name = result.data.get("dataset_name", "")

        # If aggregations are present, they represent the main evidence
        if aggregations:
            relevant_columns = list(aggregations.keys())
            claim_parts = [f"{k}: {v}" for k, v in aggregations.items()]
            claim = ", ".join(claim_parts[:4])

            items.append({
                "claim": claim,
                "source": result.source_label,
                "data": {
                    "type": "dataset",
                    "dataset_name": dataset_name,
                    "relevant_columns": relevant_columns,
                    "query_context": f"Aggregated metrics from {dataset_name}",
                    "source_file": source_file,
                },
            })
        elif records:
            # Build evidence from record data
            relevant_columns: list[str] = []
            if records and isinstance(records[0], dict):
                relevant_columns = [
                    k for k in records[0].keys()
                    if k not in ("id", "project_id", "created_at", "updated_at")
                ]

            # Summarize first few records as evidence
            claim_parts = []
            for record in records[:3]:
                if isinstance(record, dict):
                    parts = [
                        f"{k}: {v}" for k, v in record.items()
                        if v is not None and k in relevant_columns[:4]
                    ]
                    if parts:
                        claim_parts.append(", ".join(parts))

            claim = "; ".join(claim_parts) if claim_parts else "Structured data records"

            items.append({
                "claim": claim,
                "source": result.source_label,
                "data": {
                    "type": "dataset",
                    "dataset_name": dataset_name,
                    "relevant_columns": relevant_columns[:6],
                    "query_context": f"Query results from {dataset_name}",
                    "source_file": source_file,
                },
            })

        return items

    def _build_detailed_evidence(self, result: ToolResult) -> list[dict[str, Any]]:
        """Build evidence items from get_evidence results."""
        items: list[dict[str, Any]] = []
        if not isinstance(result.data, dict):
            return items
        evidence_payload = result.data.get("evidence", {})
        evidence_type = result.data.get("evidence_type", "document")

        if not isinstance(evidence_payload, dict):
            return items

        excerpt = evidence_payload.get("excerpt", "")
        file_name = evidence_payload.get("file_name", "")
        sheet_name = evidence_payload.get("sheet_name")
        region = evidence_payload.get("region")
        section = evidence_payload.get("section", "")

        # Determine evidence type based on metadata
        if sheet_name or region:
            data_type = "excel"
        elif evidence_type == "structured":
            data_type = "dataset"
        else:
            data_type = "document"

        claim = excerpt[:150] if excerpt else f"Evidence from {file_name}"

        items.append({
            "claim": claim,
            "source": result.source_label,
            "data": {
                "type": data_type,
                "file_name": file_name,
                "page_or_section": section or None,
                "text_excerpt": excerpt,
                "sheet_name": sheet_name,
                "region": region,
            },
        })

        return items

    def _build_trace(
        self,
        query_id: UUID,
        conversation_id: UUID,
        question: str,
        project_id: UUID,
        agent_response: AgentResponse,
        duration_ms: int,
    ) -> QueryTrace:
        """Build a structured trace record from the completed query execution.

        Args:
            query_id: Unique query identifier.
            conversation_id: Conversation this query belongs to.
            question: The user's original question.
            project_id: Project context used.
            agent_response: The agent's response including tool results.
            duration_ms: Total execution duration.

        Returns:
            A QueryTrace capturing the full execution path.
        """
        tool_traces: list[ToolInvocationTrace] = []
        sources_queried: list[str] = []
        failures: list[str] = []
        evidence_count = 0

        for result in agent_response.tool_results:
            data = result.data if isinstance(result.data, dict) else {}
            source_id = data.get("source_id") or result.source_label or None
            tool_traces.append(
                ToolInvocationTrace(
                    tool_name=result.tool_name,
                    source_id=source_id,
                    execution_status="success" if result.success else "failed",
                    duration_ms=result.duration_ms,
                    error=result.error,
                    records_returned=data.get("record_count", 0) if result.success else 0,
                )
            )
            if result.success and result.source_label:
                sources_queried.append(result.source_label)
                evidence_count += len(data.get("evidence", []))
            if not result.success and result.error:
                # Sanitize error before storing in trace
                failures.append(sanitize_log_value(result.error))

        # NOTE: provider name derived from the configured provider class
        provider_name = type(self._provider).__name__

        return QueryTrace(
            query_id=query_id,
            conversation_id=conversation_id,
            question=question,
            project_id=project_id,
            tools_invoked=tool_traces,
            sources_queried=sources_queried,
            evidence_count=evidence_count,
            failures=failures,
            is_partial=agent_response.is_partial,
            provider=provider_name,
            model=agent_response.model,
            duration_ms=duration_ms,
        )

    @property
    def last_trace(self) -> QueryTrace | None:
        """The trace record from the most recent query execution.

        Useful for testing and debugging. In production, traces should be
        persisted via a repository (future enhancement).
        """
        return self._last_trace
