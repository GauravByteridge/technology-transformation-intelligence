"""
Strands Agent Wrapper — bridges native Strands SDK with our AIService contract.

Owns: project scoping, response contract transformation, evidence collection.
Delegates to Strands: tool selection, reasoning, multi-step execution, LLM calls.

The Strands SDK (strands-agents) provides:
- Agent class with built-in reasoning loop and tool orchestration
- OpenAIModel adapter for Azure OpenAI, Groq, and other OpenAI-compatible APIs
- @tool decorator for automatic tool schema extraction
- SlidingWindowConversationManager for conversation history

This wrapper does NOT reimplement:
- Reasoning loop (Strands handles it)
- Tool description registry (Strands extracts from @tool docstrings)
- Function call parsing (Strands handles it internally)
- Custom LLM adapters (OpenAIModel covers all our providers)

Security Invariants:
- Never receives database credentials or connection strings.
- Never exposes internal tool names or implementation paths to users.
- Error messages are sanitized before reaching the response contract.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.ai.agent import AgentResponse, ToolResult
from app.ai.prompt_manager import PromptManager
from app.ai.trace import sanitize_log_value
from app.config.settings import Settings

logger = logging.getLogger(__name__)


class StrandsAgentWrapper:
    """Wraps the native Strands Agent for AIService integration.

    Responsibilities:
    - Create the Strands Agent with configured model and tools
    - Inject project context into prompts
    - Transform Strands results into AgentResponse contract
    - Collect evidence and source attribution from tool results

    Does NOT own:
    - Tool selection logic (Strands Agent handles this)
    - Multi-step reasoning (Strands Agent handles this)
    - LLM API calls (Strands Agent + OpenAIModel handle this)
    """

    def __init__(
        self,
        settings: Settings,
        tools: list,
        system_prompt: str,
    ) -> None:
        """Initialize the Strands Agent wrapper.

        Args:
            settings: Application settings with LLM provider configuration.
            tools: List of @tool-decorated functions for the agent.
            system_prompt: The system prompt instructing agent behavior.
        """
        self._settings = settings
        self._tools = tools
        self._system_prompt = system_prompt
        self._agent = self._create_agent()

    def _create_agent(self):
        """Create the Strands Agent with configured model and tools."""
        from strands import Agent
        from strands.agent.conversation_manager import SlidingWindowConversationManager

        model = self._create_model()

        agent = Agent(
            model=model,
            tools=self._tools,
            system_prompt=self._system_prompt,
            conversation_manager=SlidingWindowConversationManager(window_size=20),
        )

        logger.info(
            "strands_agent_created",
            extra={
                "tool_count": len(self._tools),
                "provider": self._settings.llm_provider or "mock",
            },
        )

        return agent

    def _create_model(self):
        """Create the appropriate OpenAIModel adapter from settings.

        Uses the Strands OpenAIModel which works with any OpenAI-compatible API:
        - Azure OpenAI (via AzureOpenAI client)
        - Azure AI Foundry (via OpenAI client with custom base_url)
        - Groq (via OpenAI client with Groq base_url)
        """
        from strands.models.openai import OpenAIModel

        settings = self._settings

        if settings.llm_provider == "azure_openai":
            from openai import AzureOpenAI

            client = AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
            return OpenAIModel(
                client=client,
                model_id=settings.azure_openai_deployment or "gpt-4",
            )

        elif settings.llm_provider == "azure_foundry":
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.azure_foundry_api_key,
                base_url=settings.azure_foundry_endpoint,
            )
            return OpenAIModel(
                client=client,
                model_id=settings.azure_foundry_model or "gpt-4",
            )

        elif settings.llm_provider == "groq":
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            return OpenAIModel(
                client=client,
                model_id=settings.groq_model or "llama-3.1-70b-versatile",
            )

        else:
            # Mock/demo mode — use a mock model that returns placeholder responses
            return _MockStrandsModel()

    async def invoke(
        self,
        question: str,
        project_id: UUID,
        query_id: UUID,
    ) -> AgentResponse:
        """Invoke the Strands agent with the user question.

        Injects project context, runs the Strands reasoning loop, and
        transforms the result into our AgentResponse contract.

        Args:
            question: The user's natural-language question.
            project_id: Project context for scoping data retrieval.
            query_id: Unique identifier for this query execution.

        Returns:
            AgentResponse compatible with existing AIService._build_response.
        """
        logger.info(
            "strands_agent_invoke_started",
            extra={
                "query_id": str(query_id),
                "project_id": str(project_id),
                "question_length": len(question),
            },
        )

        # Inject project context into the prompt so tools can use the correct project_id
        contextualized_prompt = (
            f"Project context — Project ID: {project_id}\n\n"
            f"User question: {question}"
        )

        try:
            # Call the Strands Agent — it handles tool selection, chaining, and synthesis
            result = self._agent(contextualized_prompt)

            # Transform into our AgentResponse contract
            response = self._build_agent_response(result, query_id)

            logger.info(
                "strands_agent_invoke_completed",
                extra={
                    "query_id": str(query_id),
                    "answer_length": len(response.answer),
                    "is_partial": response.is_partial,
                },
            )

            return response

        except Exception as exc:
            safe_error = sanitize_log_value(str(exc))
            logger.error(
                "strands_agent_invoke_failed",
                extra={
                    "query_id": str(query_id),
                    "error": safe_error,
                },
            )

            return AgentResponse(
                answer=(
                    "I encountered an error while processing your question. "
                    "Please try again or rephrase your query."
                ),
                model=self._settings.llm_provider or "unknown",
                tool_results=[],
                is_partial=True,
            )

    def _build_agent_response(self, result, query_id: UUID) -> AgentResponse:
        """Transform Strands AgentResult into our AgentResponse format.

        Extracts the text answer and builds tool result metadata from
        the Strands execution trace.

        Args:
            result: The Strands agent result object.
            query_id: Query identifier for tracing.

        Returns:
            AgentResponse with answer, model, and tool_results.
        """
        # Extract the text answer from the Strands result
        answer = str(result) if result else "No answer generated."

        # Build tool results from available metadata
        tool_results = self._extract_tool_results(result)

        # Determine if response is partial (any tool failures)
        is_partial = any(not tr.success for tr in tool_results)

        model_name = self._settings.llm_provider or "mock"

        return AgentResponse(
            answer=answer,
            model=model_name,
            tool_results=tool_results,
            is_partial=is_partial,
        )

    def _extract_tool_results(self, result) -> list[ToolResult]:
        """Extract tool invocation results from Strands agent execution.

        Attempts to extract tool call information from the Strands result
        for source attribution and evidence tracking.

        Args:
            result: The Strands agent result object.

        Returns:
            List of ToolResult objects representing tool invocations.
        """
        tool_results: list[ToolResult] = []

        try:
            # Strands stores tool results in the message history
            if hasattr(result, "messages") and result.messages:
                for message in result.messages:
                    if isinstance(message, dict) and message.get("role") == "tool":
                        content = message.get("content", "")
                        tool_name = message.get("name", "unknown")
                        tool_results.append(
                            ToolResult(
                                tool_name=tool_name,
                                success=True,
                                data={
                                    "content": content,
                                    "source_type": "tool_result",
                                },
                                source_label=self._get_source_label(tool_name),
                            )
                        )
        except Exception as exc:
            # Non-critical — we can still return the answer without tool metadata
            logger.debug(
                "strands_tool_result_extraction_failed",
                extra={"error": str(exc)},
            )

        return tool_results

    def _get_source_label(self, tool_name: str) -> str:
        """Map internal tool names to human-readable source labels.

        Ensures no internal implementation details leak to the user.

        Args:
            tool_name: The internal tool function name.

        Returns:
            A human-readable source label.
        """
        label_map = {
            "search_documents": "Document Search",
            "get_evidence": "Evidence Retrieval",
            "query_dataset": "Structured Dataset Query",
            "list_available_datasets": "Dataset Discovery",
            "get_dataset_metadata": "Dataset Metadata",
        }
        return label_map.get(tool_name, "Enterprise Data")


class _MockStrandsModel:
    """Mock model for demo/test mode when no LLM provider is configured.

    Implements the Strands Model interface minimally so that the Agent
    can be instantiated without a real LLM backend. Returns a placeholder
    response indicating demo mode.
    """

    def __init__(self) -> None:
        self.model_id = "mock"
        self._config: dict = {}

    @property
    def stateful(self) -> bool:
        """Mock model is not stateful."""
        return False

    def update_config(self, **model_config) -> None:
        """Accept config updates (no-op for mock)."""
        self._config.update(model_config)

    def get_config(self) -> dict:
        """Return current config."""
        return self._config

    def count_tokens(self, messages=None, tool_specs=None, system_prompt=None, **kwargs) -> int:
        """Return a fixed token count estimate."""
        return 100

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        """Yield mock response events in Strands StreamEvent format.

        Mimics the Strands streaming protocol with a complete text response.
        """
        from strands.types.streaming import StreamEvent

        # Extract the user question from messages for a helpful mock response
        user_question = ""
        for msg in reversed(messages or []):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("text"):
                            user_question = block["text"]
                            break
                elif isinstance(content, str):
                    user_question = content
                break

        mock_answer = (
            "I'm running in demo mode without an LLM provider configured. "
            "To get intelligent responses, configure an LLM provider "
            "(azure_openai, azure_foundry, or groq) in your environment. "
            f"Your question was: {user_question[:200]}"
        )

        yield StreamEvent(messageStart={"role": "assistant"})
        yield StreamEvent(contentBlockStart={"start": {"text": ""}, "contentBlockIndex": 0})
        yield StreamEvent(contentBlockDelta={"delta": {"text": mock_answer}, "contentBlockIndex": 0})
        yield StreamEvent(contentBlockStop={"contentBlockIndex": 0})
        yield StreamEvent(messageStop={"stopReason": "end_turn", "additionalModelResponseFields": None})

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        """Not supported in mock mode."""
        raise NotImplementedError("Structured output not supported in mock mode")
