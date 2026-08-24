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
            if result.success:
                # Safety: ensure data is a dict before accessing with .get()
                data = result.data if isinstance(result.data, dict) else {"raw": result.data}

                source_entry = {
                    "name": result.source_label,
                    "type": data.get("source_type", "unknown"),
                    "records_returned": data.get("record_count", 0),
                }

                # Enrich source record count from tool-specific fields
                if "result_count" in data:
                    source_entry["records_returned"] = data["result_count"]
                elif "total_count" in data:
                    source_entry["records_returned"] = data["total_count"]
                elif "dataset_count" in data:
                    source_entry["records_returned"] = data["dataset_count"]

                sources.append(source_entry)

                # Build typed evidence items based on the tool that produced them
                tool_evidence = self._extract_typed_evidence(result)
                evidence.extend(tool_evidence)
            else:
                failed_sources.append({
                    "source": result.source_label or result.tool_name,
                    "error": sanitize_log_value(result.error) if result.error else "Unknown error",
                })

        return AIResponse(
            answer=strip_markup(agent_response.answer),
            response_type="text",
            sources=sources,
            evidence=evidence,
            query_id=query_id,
            conversation_id=conversation_id,
            is_partial=agent_response.is_partial,
            failed_sources=failed_sources,
        )

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

        if result.tool_name == "search_documents":
            evidence_items.extend(self._build_document_evidence(result))
        elif result.tool_name == "query_dataset":
            evidence_items.extend(self._build_dataset_evidence(result))
        elif result.tool_name == "get_evidence":
            evidence_items.extend(self._build_detailed_evidence(result))
        elif result.tool_name in ("list_available_datasets", "get_dataset_metadata"):
            # Informational tools — don't produce user-facing evidence items
            pass
        else:
            # Generic fallback — use any evidence items in the result data
            tool_evidence = result.data.get("evidence", [])
            for item in tool_evidence:
                evidence_items.append({
                    "claim": item.get("claim", ""),
                    "source": result.source_label,
                    "data": item.get("data"),
                })

        return evidence_items

    def _build_document_evidence(self, result: ToolResult) -> list[dict[str, Any]]:
        """Build evidence items from search_documents results.

        Maps document search results to evidence items with type="document".
        """
        items: list[dict[str, Any]] = []
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
        """Build evidence items from query_dataset results.

        Maps structured query results to evidence items with type="dataset".
        """
        items: list[dict[str, Any]] = []
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
        """Build evidence items from get_evidence results.

        Maps detailed evidence to items typed as "document" or "excel"
        depending on the evidence metadata.
        """
        items: list[dict[str, Any]] = []
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
