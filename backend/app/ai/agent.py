"""
AI Agent — Strands integration placeholder.

Defines the agent interface and a Phase 0 simplified implementation
that invokes registered tools and delegates text synthesis to the
configured text generation provider.

In Phase 1, this will be replaced with full Strands agent wiring
where the LLM reasons about which tools to call. For Phase 0, the
agent invokes all available relevant tools and synthesizes results.

Security Invariants:
- The agent NEVER imports database drivers or ORMs.
- The agent NEVER receives credentials, connection strings, or tokens.
- The agent accesses data exclusively through registered tool functions.
- Tool results are the only source of external information for the agent.
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.ai.providers.protocol import TextGenerationProvider
from app.ai.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolResult:
    """Result from a single tool invocation.

    Attributes:
        tool_name: The business-intent name of the invoked tool.
        success: Whether the tool executed without errors.
        data: The data returned by the tool (empty dict on failure).
        source_label: Human-readable label for source attribution.
        error: Error message if the tool failed, None otherwise.
        duration_ms: Time taken for the tool invocation in milliseconds.
    """

    tool_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    source_label: str = ""
    error: str | None = None
    duration_ms: int = 0


@dataclass(frozen=True)
class AgentResponse:
    """Aggregated response from the agent after tool invocations.

    Attributes:
        answer: Synthesized text answer from the LLM.
        model: The model that generated the answer.
        tool_results: Results from each tool invocation.
        is_partial: True if some tools failed during execution.
    """

    answer: str
    model: str
    tool_results: list[ToolResult] = field(default_factory=list)
    is_partial: bool = False


class AIAgent:
    """Phase 0 AI Agent — simplified tool invocation and synthesis.

    In Phase 0, the agent follows a straightforward pattern:
    1. Determine which tools are relevant to the question
    2. Invoke each relevant tool with the project context
    3. Collect results (handling partial failures gracefully)
    4. Call the text generation provider to synthesize an answer

    In Phase 1, Strands will replace steps 1-2 with LLM-driven
    reasoning about which tools to call and in what order.

    The agent NEVER:
    - Imports database drivers or connection libraries
    - Receives credentials or connection strings
    - Bypasses tools to access data directly
    """

    def __init__(
        self,
        provider: TextGenerationProvider,
        tool_registry: ToolRegistry,
    ) -> None:
        """Initialize the AI agent.

        Args:
            provider: Text generation provider for answer synthesis.
            tool_registry: Registry of available domain-scoped tools.
        """
        self._provider = provider
        self._tool_registry = tool_registry

    async def invoke(
        self,
        question: str,
        project_id: UUID,
        query_id: UUID,
        tools_to_invoke: list[str] | None = None,
    ) -> AgentResponse:
        """Invoke tools and synthesize an answer for the given question.

        Args:
            question: The user's natural-language question.
            project_id: The project context for scoping queries.
            query_id: Unique identifier for tracing this query execution.
            tools_to_invoke: Specific tool names to call. If None, calls all
                registered tools (Phase 0 behavior — Phase 1 uses LLM reasoning).

        Returns:
            AgentResponse with synthesized answer and tool results.
        """
        target_tools = tools_to_invoke or self._tool_registry.list_tools()

        logger.info(
            "agent_invocation_started",
            extra={
                "query_id": str(query_id),
                "project_id": str(project_id),
                "tools_planned": target_tools,
            },
        )

        tool_results = await self._invoke_tools(
            tools=target_tools,
            project_id=project_id,
            query_id=query_id,
        )

        successful_results = [r for r in tool_results if r.success]
        failed_results = [r for r in tool_results if not r.success]
        is_partial = len(failed_results) > 0

        if failed_results:
            logger.warning(
                "agent_partial_tool_failures",
                extra={
                    "query_id": str(query_id),
                    "failed_tools": [r.tool_name for r in failed_results],
                },
            )

        # Synthesize answer from successful tool data
        answer, model = await self._synthesize_answer(
            question=question,
            tool_results=successful_results,
            project_id=project_id,
        )

        logger.info(
            "agent_invocation_completed",
            extra={
                "query_id": str(query_id),
                "tools_succeeded": len(successful_results),
                "tools_failed": len(failed_results),
                "is_partial": is_partial,
            },
        )

        return AgentResponse(
            answer=answer,
            model=model,
            tool_results=tool_results,
            is_partial=is_partial,
        )

    async def _invoke_tools(
        self,
        tools: list[str],
        project_id: UUID,
        query_id: UUID,
    ) -> list[ToolResult]:
        """Invoke each tool and collect results, handling failures gracefully.

        Args:
            tools: List of tool names to invoke.
            project_id: Project context for tool scoping.
            query_id: Query ID for tracing.

        Returns:
            List of ToolResult objects (both successes and failures).
        """
        import time

        results: list[ToolResult] = []

        for tool_name in tools:
            if not self._tool_registry.has_tool(tool_name):
                logger.warning(
                    "agent_tool_not_found",
                    extra={"tool_name": tool_name, "query_id": str(query_id)},
                )
                results.append(
                    ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error=f"Tool '{tool_name}' not registered",
                    )
                )
                continue

            start_time = time.perf_counter()
            try:
                tool_fn = self._tool_registry.get_tool(tool_name)
                data = await tool_fn(project_id=project_id)
                duration_ms = int((time.perf_counter() - start_time) * 1000)

                source_label = data.get("source_label", tool_name)
                results.append(
                    ToolResult(
                        tool_name=tool_name,
                        success=True,
                        data=data,
                        source_label=source_label,
                        duration_ms=duration_ms,
                    )
                )
                logger.debug(
                    "agent_tool_success",
                    extra={
                        "tool_name": tool_name,
                        "query_id": str(query_id),
                        "source_id": data.get("source_id", source_label),
                        "execution_status": "success",
                        "duration_ms": duration_ms,
                        "records_returned": data.get("record_count", 0),
                    },
                )
            except Exception as exc:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                # NOTE: Error messages are logged as-is here; the trace layer
                # applies sanitization before persistence or external exposure.
                logger.error(
                    "agent_tool_failed",
                    extra={
                        "tool_name": tool_name,
                        "query_id": str(query_id),
                        "execution_status": "failed",
                        "error": str(exc),
                        "duration_ms": duration_ms,
                    },
                )
                results.append(
                    ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error=str(exc),
                        duration_ms=duration_ms,
                    )
                )

        return results

    async def _synthesize_answer(
        self,
        question: str,
        tool_results: list[ToolResult],
        project_id: UUID,
    ) -> tuple[str, str]:
        """Call the text generation provider to synthesize an answer.

        Builds a prompt from the question and collected tool data,
        then calls the provider for text generation.

        Args:
            question: The user's original question.
            tool_results: Successfully completed tool results.
            project_id: Project context identifier.

        Returns:
            Tuple of (answer_text, model_name).
        """
        if not tool_results:
            # No data available — inform user rather than hallucinating
            return (
                "I was unable to retrieve sufficient information to answer your question. "
                "The requested data sources may be unavailable.",
                "none",
            )

        # Build context from tool results for the LLM
        context_parts: list[str] = []
        for result in tool_results:
            context_parts.append(
                f"[Source: {result.source_label}]\n{_summarize_tool_data(result.data)}"
            )

        context_block = "\n\n".join(context_parts)

        prompt = (
            f"Based on the following data retrieved for project {project_id}:\n\n"
            f"{context_block}\n\n"
            f"Answer the following question:\n{question}"
        )

        system_prompt = (
            "You are an AI assistant for the Technology Transformation Intelligence platform. "
            "Provide concise, accurate answers based only on the data provided. "
            "Always cite which sources support your claims. "
            "If the data is insufficient, say so clearly."
        )

        generation_result = await self._provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        return generation_result.text, generation_result.model


def _summarize_tool_data(data: dict[str, Any]) -> str:
    """Create a text summary of tool data for inclusion in the LLM prompt.

    Converts the tool's response dict into a readable string representation
    suitable for the LLM to reason over.

    Args:
        data: The dict returned by a tool function.

    Returns:
        A string summary of the tool's data.
    """
    # Remove internal metadata keys before presenting to LLM
    display_data = {k: v for k, v in data.items() if k != "source_label"}

    if not display_data:
        return "(no data returned)"

    parts: list[str] = []
    for key, value in display_data.items():
        if isinstance(value, list):
            parts.append(f"{key}: {len(value)} items")
            for item in value[:5]:  # Limit to avoid prompt overflow
                parts.append(f"  - {item}")
            if len(value) > 5:
                parts.append(f"  ... and {len(value) - 5} more")
        else:
            parts.append(f"{key}: {value}")

    return "\n".join(parts)
