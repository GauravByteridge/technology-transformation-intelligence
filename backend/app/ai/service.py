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

from app.ai.agent import AIAgent, AgentResponse
from app.ai.prompt_manager import PromptManager
from app.ai.providers.protocol import TextGenerationProvider
from app.ai.response import strip_markup
from app.ai.tools.registry import ToolRegistry
from app.ai.trace import QueryTrace, ToolInvocationTrace, sanitize_log_value
from app.schemas.ai import AIResponse

if TYPE_CHECKING:
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
    """

    def __init__(
        self,
        provider: TextGenerationProvider,
        tool_registry: ToolRegistry,
        prompt_manager: PromptManager | None = None,
        strands_agent: "StrandsAgentWrapper | None" = None,
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
        """
        self._provider = provider
        self._tool_registry = tool_registry
        self._prompt_manager = prompt_manager
        self._strands_agent = strands_agent
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

        Flow:
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
            },
        )

        try:
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
                    "execution_status": "failed",
                },
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

    def _build_response(
        self,
        agent_response: AgentResponse,
        query_id: UUID,
        conversation_id: UUID,
    ) -> AIResponse:
        """Transform an AgentResponse into the structured AIResponse contract.

        Maps tool results into sources and evidence arrays with meaningful
        labels (not internal tool names or function signatures).

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
                sources.append({
                    "name": result.source_label,
                    "type": result.data.get("source_type", "unknown"),
                    "records_returned": result.data.get("record_count", 0),
                })

                # Extract evidence items if the tool provided them
                tool_evidence = result.data.get("evidence", [])
                for item in tool_evidence:
                    evidence.append({
                        "claim": item.get("claim", ""),
                        "source": result.source_label,
                        "data": item.get("data"),
                    })
            else:
                failed_sources.append({
                    "source": result.source_label or result.tool_name,
                    "error": result.error or "Unknown error",
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
            source_id = result.data.get("source_id") or result.source_label or None
            tool_traces.append(
                ToolInvocationTrace(
                    tool_name=result.tool_name,
                    source_id=source_id,
                    execution_status="success" if result.success else "failed",
                    duration_ms=result.duration_ms,
                    error=result.error,
                    records_returned=result.data.get("record_count", 0) if result.success else 0,
                )
            )
            if result.success and result.source_label:
                sources_queried.append(result.source_label)
                evidence_count += len(result.data.get("evidence", []))
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
