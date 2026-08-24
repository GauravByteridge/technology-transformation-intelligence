"""
Cross-Source Orchestrator — coordinates catalog-aware multi-source query execution.

Responsibility split:
- Strands/LLM decides WHAT it needs (which tools/sources based on catalog context)
- CrossSourceOrchestrator EXECUTES the selected sources independently (failure isolation)

The orchestrator handles:
1. Catalog context injection → Strands Agent system prompt
2. Strands Agent invocation (dynamic tool selection)
3. Independent source execution with failure isolation
4. Evidence building from successful tool results
5. Lineage recording for full execution traceability

Key principle: One source failure does NOT block other sources.

Security Invariants:
- Never passes credentials to Strands or the LLM prompt.
- Source IDs and metadata only — connector resolves credentials server-side.
- Error messages are sanitized before inclusion in results.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.ai.agent import AgentResponse, ToolResult
from app.ai.catalog_context import CatalogContext, CatalogContextInjector
from app.ai.evidence_builder import EvidenceBuilder
from app.ai.lineage_recorder import LineageRecorder
from app.ai.trace import sanitize_log_value

logger = logging.getLogger(__name__)


@dataclass
class CrossSourceResult:
    """Result from cross-source query execution.

    Contains the synthesized answer with full evidence, lineage, and
    failure information for the enhanced AIResponse.

    Attributes:
        answer: The synthesized text answer from the LLM.
        model: The model that produced the answer.
        sources_consulted: List of source dicts that were successfully queried.
        failed_sources: List of source dicts that failed during execution.
        evidence: Structured evidence items linking claims to data.
        lineage_trace: Full execution path for transparency.
        groundedness: Groundedness classifications for evidence items.
        is_partial: True if some sources failed during execution.
        tool_results: Raw tool results for backward compatibility with _build_response.
    """

    answer: str = ""
    model: str = ""
    sources_consulted: list[dict[str, Any]] = field(default_factory=list)
    failed_sources: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    lineage_trace: dict[str, Any] = field(default_factory=dict)
    groundedness: list[dict[str, Any]] = field(default_factory=list)
    is_partial: bool = False
    tool_results: list[ToolResult] = field(default_factory=list)


class CrossSourceOrchestrator:
    """Orchestrates cross-source intelligence with failure isolation.

    Coordinates the full Phase 8 flow:
    1. Catalog context lookup (CatalogContextInjector)
    2. Strands Agent invocation with catalog-enriched prompt
    3. Independent tool execution with failure isolation
    4. Evidence building from successful results
    5. Lineage recording throughout

    The orchestrator is injected into AIService and used ONLY in real mode
    (when a real LLM provider is configured). Demo mode bypasses it entirely.
    """

    def __init__(
        self,
        strands_agent: Any,
        catalog_context_injector: CatalogContextInjector,
        evidence_builder: EvidenceBuilder,
    ) -> None:
        """Initialize the orchestrator with its dependencies.

        Args:
            strands_agent: The StrandsAgentWrapper for LLM-driven tool selection.
            catalog_context_injector: Builds relevant catalog context for prompts.
            evidence_builder: Converts tool results into structured evidence items.
        """
        self._strands_agent = strands_agent
        self._catalog_context_injector = catalog_context_injector
        self._evidence_builder = evidence_builder

    async def execute_cross_source_query(
        self,
        question: str,
        project_id: UUID,
        query_id: UUID,
    ) -> CrossSourceResult:
        """Execute a cross-source query with full evidence and lineage.

        Flow:
        1. Build relevant catalog context for the question/project
        2. Record catalog lookup in lineage
        3. Invoke Strands Agent (which dynamically selects tools based on catalog)
        4. Collect tool results (Strands handles independent execution)
        5. Build evidence from successful results
        6. Classify groundedness
        7. Finalize lineage trace
        8. Return CrossSourceResult with all Phase 8 fields

        Args:
            question: The user's natural-language question.
            project_id: Project context for scoping data retrieval.
            query_id: Unique identifier for this query execution.

        Returns:
            CrossSourceResult containing answer, evidence, lineage, and source info.
        """
        lineage = LineageRecorder()
        lineage.start_trace(query_id, question)

        start_time = time.perf_counter()

        # Step 1: Build catalog context
        catalog_context = await self._build_catalog_context(
            question, project_id, lineage
        )

        # Step 2: Inject catalog context into Strands Agent and invoke
        agent_response = await self._invoke_with_catalog_context(
            question, project_id, query_id, catalog_context, lineage
        )

        # Step 3: Record tool invocations in lineage from agent response
        self._record_tool_invocations(agent_response, lineage)

        # Step 4: Build evidence from successful tool results
        evidence = self._build_evidence(agent_response.tool_results)

        # Step 5: Classify groundedness for each evidence item
        groundedness = self._classify_groundedness(evidence, agent_response.answer)

        # Step 6: Build sources_consulted and failed_sources
        sources_consulted, failed_sources = self._partition_sources(
            agent_response.tool_results
        )

        # Step 7: Finalize lineage
        answer_generated = bool(agent_response.answer)
        lineage_trace = lineage.finalize_trace(answer_generated)

        is_partial = agent_response.is_partial or len(failed_sources) > 0

        logger.info(
            "cross_source_query_completed",
            extra={
                "query_id": str(query_id),
                "sources_consulted": len(sources_consulted),
                "failed_sources": len(failed_sources),
                "evidence_items": len(evidence),
                "is_partial": is_partial,
                "duration_ms": int((time.perf_counter() - start_time) * 1000),
            },
        )

        return CrossSourceResult(
            answer=agent_response.answer,
            model=agent_response.model,
            sources_consulted=sources_consulted,
            failed_sources=failed_sources,
            evidence=evidence,
            lineage_trace=lineage_trace,
            groundedness=groundedness,
            is_partial=is_partial,
            tool_results=agent_response.tool_results,
        )

    async def _build_catalog_context(
        self,
        question: str,
        project_id: UUID,
        lineage: LineageRecorder,
    ) -> CatalogContext:
        """Look up the catalog for relevant entries and record in lineage.

        Args:
            question: User's question for relevance matching.
            project_id: Project scope for prioritization.
            lineage: Lineage recorder to capture the lookup step.

        Returns:
            CatalogContext with ranked relevant entries.
        """
        lookup_start = time.perf_counter()

        try:
            catalog_context = (
                await self._catalog_context_injector.build_relevant_context(
                    question=question,
                    project_id=project_id,
                )
            )

            duration_ms = int((time.perf_counter() - lookup_start) * 1000)
            lineage.record_catalog_lookup(
                entries_found=catalog_context.total_available,
                entries_used=catalog_context.included_count,
                duration_ms=duration_ms,
            )

            return catalog_context

        except Exception as exc:
            duration_ms = int((time.perf_counter() - lookup_start) * 1000)
            logger.warning(
                "catalog_context_lookup_failed",
                extra={"error": sanitize_log_value(str(exc))},
            )
            # Record the failure but continue — the agent can still function
            # without catalog context (it just won't have source awareness)
            lineage.record_catalog_lookup(
                entries_found=0,
                entries_used=0,
                duration_ms=duration_ms,
            )
            return CatalogContext()

    async def _invoke_with_catalog_context(
        self,
        question: str,
        project_id: UUID,
        query_id: UUID,
        catalog_context: CatalogContext,
        lineage: LineageRecorder,
    ) -> AgentResponse:
        """Invoke the Strands Agent with catalog context injected.

        The catalog context is formatted as a semantic information landscape
        and prepended to the agent's understanding of available data.

        Args:
            question: User's natural-language question.
            project_id: Project scope.
            query_id: Query identifier.
            catalog_context: Relevant catalog entries for context.
            lineage: Lineage recorder for tracing.

        Returns:
            AgentResponse from the Strands Agent.
        """
        # Format catalog context for the LLM — it's injected via the
        # contextualized prompt alongside the project ID and question.
        # NOTE: The Strands Agent receives this as part of the user message
        # because the system prompt is set at initialization time. The
        # catalog context varies per query, so it goes in the user prompt.
        catalog_prompt_section = self._catalog_context_injector.format_for_system_prompt(
            catalog_context
        )

        # The StrandsAgentWrapper.invoke() adds project context and calls
        # the Strands Agent. We augment the question with catalog context.
        augmented_question = question
        if catalog_prompt_section and catalog_context.included_count > 0:
            augmented_question = (
                f"{catalog_prompt_section}\n\n"
                f"---\n\n"
                f"{question}"
            )

        return await self._strands_agent.invoke(
            question=augmented_question,
            project_id=project_id,
            query_id=query_id,
        )

    def _record_tool_invocations(
        self,
        agent_response: AgentResponse,
        lineage: LineageRecorder,
    ) -> None:
        """Record each tool invocation from the agent response into lineage.

        Args:
            agent_response: The completed agent response with tool results.
            lineage: The lineage recorder to append steps to.
        """
        for result in agent_response.tool_results:
            source_id = result.data.get("source_id", "")
            source_name = result.source_label or result.tool_name
            object_name = result.data.get("object_name", "")

            # Extract from source_metadata if present (connector tool format)
            source_metadata = result.data.get("source_metadata", {})
            if source_metadata:
                source_id = source_metadata.get("source_id", source_id)
                source_name = source_metadata.get("source_name", source_name)
                object_name = source_metadata.get("object_name", object_name)

            status = "success" if result.success else "failed"
            records_count = result.data.get("row_count", 0)
            if not records_count:
                records_count = result.data.get("record_count", 0)

            lineage.record_tool_invocation(
                tool_name=result.tool_name,
                source_id=str(source_id),
                source_name=source_name,
                object_name=object_name,
                status=status,
                duration_ms=result.duration_ms,
                records_count=records_count,
                # Sanitize error to prevent credential leakage in lineage trace
                error=sanitize_log_value(result.error) if result.error else None,
            )

    def _build_evidence(
        self, tool_results: list[ToolResult]
    ) -> list[dict[str, Any]]:
        """Build structured evidence items from successful tool results.

        Only successful tool results produce evidence — failed tools
        contribute nothing to evidence (no fabrication).

        Args:
            tool_results: All tool results from agent execution.

        Returns:
            List of structured evidence item dicts.
        """
        # Convert ToolResult objects to the dict format expected by EvidenceBuilder
        successful_result_dicts: list[dict[str, Any]] = []

        for result in tool_results:
            if not result.success:
                continue
            successful_result_dicts.append(result.data)

        return self._evidence_builder.build_evidence(successful_result_dicts)

    def _classify_groundedness(
        self,
        evidence: list[dict[str, Any]],
        answer: str,
    ) -> list[dict[str, Any]]:
        """Classify the groundedness of each evidence item.

        Categories:
        - "retrieved_fact": Directly from data source
        - "derived_calculation": Computed from retrieved data
        - "ai_explanation": LLM reasoning without direct data support

        Args:
            evidence: Evidence items to classify.
            answer: The synthesized answer text for context.

        Returns:
            List of groundedness classification dicts.
        """
        classifications: list[dict[str, Any]] = []

        for item in evidence:
            claim = item.get("excerpt", item.get("claim", ""))
            classification = self._evidence_builder.classify_groundedness(
                claim=claim,
                evidence=item,
            )
            classifications.append({
                "evidence_id": item.get("evidence_id", ""),
                "classification": classification,
                "claim": claim[:200] if claim else "",
            })

        return classifications

    def _partition_sources(
        self, tool_results: list[ToolResult]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Partition tool results into sources_consulted and failed_sources.

        Only actually-queried sources appear in sources_consulted.
        Failed sources appear separately with user-friendly error descriptions.

        Args:
            tool_results: All tool results from agent execution.

        Returns:
            Tuple of (sources_consulted, failed_sources).
        """
        sources_consulted: list[dict[str, Any]] = []
        failed_sources: list[dict[str, Any]] = []

        for result in tool_results:
            source_metadata = result.data.get("source_metadata", {})
            source_id = source_metadata.get("source_id", result.data.get("source_id", ""))
            source_name = source_metadata.get("source_name", result.source_label)
            source_type = source_metadata.get("source_type", result.data.get("source_type", "unknown"))
            object_name = source_metadata.get("object_name", result.data.get("object_name", ""))

            if result.success:
                records_returned = result.data.get("row_count", 0)
                if not records_returned:
                    records_returned = result.data.get("record_count", 0)

                sources_consulted.append({
                    "source_id": source_id,
                    "source_type": source_type,
                    "source_name": source_name,
                    "object_name": object_name,
                    "records_returned": records_returned,
                    "query_duration_ms": result.duration_ms,
                })
            else:
                # User-friendly error — never expose credentials or stack traces
                safe_error = sanitize_log_value(result.error or "Source unavailable")
                failed_sources.append({
                    "source_id": source_id,
                    "source_type": source_type,
                    "source_name": source_name,
                    "error": safe_error,
                })

        return sources_consulted, failed_sources
