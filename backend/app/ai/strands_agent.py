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
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            return OpenAIModel(
                client=client,
                model_id=settings.groq_model or "openai/gpt-oss-120b",
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
            # Strands Agent __call__ is synchronous but works with async models internally
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._agent, contextualized_prompt
            )

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
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
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
        the Strands agent's conversation history.

        Args:
            result: The Strands agent result object.
            query_id: Query identifier for tracing.

        Returns:
            AgentResponse with answer, model, and tool_results.
        """
        # Extract the text answer from the Strands result
        answer = str(result) if result else "No answer generated."

        # Build tool results from the agent's conversation messages
        tool_results = self._extract_tool_results_from_agent()

        # Determine if response is partial (any tool failures)
        is_partial = any(not tr.success for tr in tool_results)

        model_name = self._settings.llm_provider or "mock"

        return AgentResponse(
            answer=answer,
            model=model_name,
            tool_results=tool_results,
            is_partial=is_partial,
        )

    def _extract_tool_results_from_agent(self) -> list[ToolResult]:
        """Extract tool invocation results from the agent's conversation history.

        The Strands Agent stores conversation messages in `agent.messages`.
        Tool results appear as `toolResult` content blocks inside user messages.
        Tool invocations appear as `toolUse` blocks in assistant messages.

        Returns:
            List of ToolResult objects with full structured data from tools.
        """
        import json

        tool_results: list[ToolResult] = []

        try:
            messages = getattr(self._agent, "messages", [])
            if not messages:
                return tool_results

            # Map toolUseId → tool_name from assistant messages
            tool_use_map: dict[str, str] = {}
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                if msg.get("role") == "assistant":
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and "toolUse" in block:
                                tu = block["toolUse"]
                                tool_use_id = tu.get("toolUseId", "")
                                tool_name = tu.get("name", "unknown")
                                tool_use_map[tool_use_id] = tool_name

            # Extract tool results from user messages with toolResult blocks
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                if msg.get("role") != "user":
                    continue
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or "toolResult" not in block:
                        continue
                    tr_block = block["toolResult"]
                    tool_use_id = tr_block.get("toolUseId", "")
                    tool_name = tool_use_map.get(tool_use_id, "unknown")
                    status = tr_block.get("status", "success")

                    # Extract text content from toolResult
                    tr_content = tr_block.get("content", [])
                    content_str = self._extract_text_from_tool_result_content(tr_content)

                    # Parse the content into structured data
                    tool_result = self._parse_tool_result_content(content_str, tool_name)

                    # Override success based on Strands status field
                    if status == "error":
                        tool_result = ToolResult(
                            tool_name=tool_result.tool_name,
                            success=False,
                            data=tool_result.data,
                            source_label=tool_result.source_label,
                            error=tool_result.error or "Tool execution failed",
                        )

                    tool_results.append(tool_result)

        except Exception as exc:
            logger.debug(
                "strands_tool_result_extraction_failed",
                extra={"error": str(exc)},
            )

        return tool_results

    def _extract_tool_results(self, result) -> list[ToolResult]:
        """Extract tool invocation results from Strands agent execution.

        Parses structured data from tool result messages for evidence enrichment.
        Supports both the older role="tool" format and the newer Strands format
        where tool results appear as content blocks with a `toolResult` key
        inside user messages.

        Args:
            result: The Strands agent result object.

        Returns:
            List of ToolResult objects with full structured data from tools.
        """
        import json

        tool_results: list[ToolResult] = []

        try:
            if not hasattr(result, "messages") or not result.messages:
                return tool_results

            for message in result.messages:
                if not isinstance(message, dict):
                    continue

                # Format 1: role="tool" messages (older Strands format)
                if message.get("role") == "tool":
                    tool_name = message.get("name", "unknown")
                    content = message.get("content", "")
                    tool_result = self._parse_tool_result_content(
                        content, tool_name
                    )
                    tool_results.append(tool_result)

                # Format 2: toolResult blocks inside user messages (newer Strands format)
                elif message.get("role") == "user":
                    content_blocks = message.get("content", [])
                    if not isinstance(content_blocks, list):
                        continue
                    for block in content_blocks:
                        if not isinstance(block, dict):
                            continue
                        tool_result_block = block.get("toolResult")
                        if not tool_result_block:
                            continue
                        tool_name = tool_result_block.get("name", "unknown")
                        block_content = tool_result_block.get("content", [])
                        # Extract text from the content list
                        content_str = self._extract_text_from_tool_result_content(
                            block_content
                        )
                        tool_result = self._parse_tool_result_content(
                            content_str, tool_name
                        )
                        tool_results.append(tool_result)

        except Exception as exc:
            # Non-critical — we can still return the answer without tool metadata
            logger.debug(
                "strands_tool_result_extraction_failed",
                extra={"error": str(exc)},
            )

        return tool_results

    def _parse_tool_result_content(
        self, content: Any, tool_name: str
    ) -> ToolResult:
        """Parse tool result content into a structured ToolResult.

        Attempts JSON parsing to recover the full dict returned by @tool functions.
        Detects errors via the "error" key and preserves all structured data for
        downstream evidence enrichment in _build_response().

        Args:
            content: Raw content from the tool result (string or dict).
            tool_name: The tool function name for labeling.

        Returns:
            ToolResult with parsed structured data.
        """
        import json

        parsed_data: dict[str, Any] = {}

        # Parse content — could be a JSON string, a dict, or a plain string
        if isinstance(content, dict):
            parsed_data = content
        elif isinstance(content, str):
            try:
                parsed_data = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                # Fall back to storing as plain content
                parsed_data = {"content": content, "source_type": "tool_result"}
        elif isinstance(content, list):
            # Some formats return a list of content blocks
            text_parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)
            combined = " ".join(text_parts)
            try:
                parsed_data = json.loads(combined)
            except (json.JSONDecodeError, ValueError):
                parsed_data = {"content": combined, "source_type": "tool_result"}
        else:
            parsed_data = {"content": str(content), "source_type": "tool_result"}

        # Detect errors: if parsed data contains an "error" key, mark as failed
        has_error = "error" in parsed_data and parsed_data["error"]
        error_message: str | None = None
        if has_error:
            error_message = sanitize_log_value(str(parsed_data["error"]))

        # Use source_label from parsed data if available, otherwise fall back
        source_label = parsed_data.get(
            "source_label", self._get_source_label(tool_name)
        )

        return ToolResult(
            tool_name=tool_name,
            success=not has_error,
            data=parsed_data,
            source_label=source_label,
            error=error_message,
        )

    def _extract_text_from_tool_result_content(
        self, content: Any
    ) -> str:
        """Extract text string from Strands toolResult content blocks.

        Strands toolResult content can be a list of dicts with "text" keys
        or a plain string.

        Args:
            content: The content field from a toolResult block.

        Returns:
            Combined text content as a string.
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            return " ".join(parts)
        return str(content) if content else ""

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
            "query_connected_source": "Connected Source Query",
            "discover_available_sources": "Enterprise Data Catalog",
        }
        return label_map.get(tool_name, "Enterprise Data")


class _MockStrandsModel:
    """Mock model that produces realistic tool call sequences for demo mode.

    Implements the Strands Model interface and emits tool_use streaming events
    based on deterministic question classification. This enables the full
    agent → tool → response pipeline to work without real LLM credentials.

    The QuestionClassifier dependency is intentionally scoped to this class only.
    """

    def __init__(self) -> None:
        # NOTE: QuestionClassifier imported here per dependency constraint —
        # only _MockStrandsModel may depend on it.
        from app.ai.question_classifier import QuestionClassifier

        self.model_id = "mock-demo"
        self._config: dict = {}
        self._classifier = QuestionClassifier()

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
        """Yield streaming events — either tool_use blocks or final text.

        Behavior depends on conversation state:
        - Initial call (no tool_result messages): classify question, emit tool_use
        - Continuation call (tool_result messages present): determine next step
          based on intent and which tools have already completed

        Emits valid Strands StreamEvent sequences conforming to the streaming protocol.
        """
        import json
        import uuid as uuid_mod

        from strands.types.streaming import StreamEvent

        from app.ai.question_classifier import QuestionIntent

        has_tool_results = self._has_tool_results(messages)

        if not has_tool_results:
            # Initial call — classify question and emit first tool_use
            async for event in self._emit_initial_tool_call(messages, uuid_mod):
                yield event
        else:
            # Multi-turn continuation — inspect completed tools and decide next action
            async for event in self._emit_continuation(messages, uuid_mod):
                yield event

    async def _emit_initial_tool_call(self, messages: list, uuid_mod) -> None:
        """Classify the question and emit tool_use StreamEvents for the first tool.

        Extracts user question and project_id from the conversation messages,
        classifies intent, and emits the appropriate tool_use event sequence.
        """
        import json

        from strands.types.streaming import StreamEvent

        from app.ai.question_classifier import QuestionIntent

        user_question = self._extract_user_question(messages)
        project_id = self._extract_project_id(user_question)
        search_query = self._derive_search_query(user_question)

        intent = self._classifier.classify(user_question)
        tool_use_id = str(uuid_mod.uuid4())[:8]

        # Determine tool_name and arguments based on classified intent
        if intent == QuestionIntent.QUANTITATIVE:
            tool_name = "list_available_datasets"
            arguments = {"project_id": project_id}
        else:
            # QUALITATIVE and HYBRID both start with search_documents
            tool_name = "search_documents"
            arguments = {"project_id": project_id, "query": search_query}

        arguments_json = json.dumps(arguments)

        # Emit valid Strands streaming protocol for tool_use
        yield StreamEvent(messageStart={"role": "assistant"})
        yield StreamEvent(
            contentBlockStart={
                "start": {"toolUse": {"toolUseId": tool_use_id, "name": tool_name}},
                "contentBlockIndex": 0,
            }
        )
        yield StreamEvent(
            contentBlockDelta={
                "delta": {"toolUse": {"input": arguments_json}},
                "contentBlockIndex": 0,
            }
        )
        yield StreamEvent(contentBlockStop={"contentBlockIndex": 0})
        yield StreamEvent(
            messageStop={"stopReason": "tool_use", "additionalModelResponseFields": None}
        )

    async def _emit_continuation(self, messages: list, uuid_mod) -> None:
        """Determine next action after tool results are received.

        Inspects the conversation to determine:
        1. What was the original intent (QUALITATIVE/QUANTITATIVE/HYBRID)
        2. Which tools have already been called
        3. Whether more tools are needed or synthesis should occur

        For QUALITATIVE: After search_documents result → synthesize
        For QUANTITATIVE: After list_available_datasets → emit query_dataset
                          After query_dataset result → synthesize
        For HYBRID: After search_documents → emit structured data tool
                    After all tools done → synthesize

        Dataset discovery is CONDITIONAL:
        - If dataset name is inferrable from the question → query_dataset directly
        - Otherwise → list_available_datasets first
        """
        import json

        from strands.types.streaming import StreamEvent

        from app.ai.question_classifier import QuestionIntent

        # Extract original question and classify again for intent
        user_question = self._extract_first_user_question(messages)
        project_id = self._extract_project_id(user_question)
        intent = self._classifier.classify(user_question)

        # Identify which tools have already been called
        completed_tools = self._get_completed_tools(messages)
        tool_results_data = self._extract_all_tool_result_data(messages)

        # Determine if we need more tool calls or should synthesize
        next_tool = self._determine_next_tool(
            intent, completed_tools, tool_results_data, user_question, project_id
        )

        if next_tool is not None:
            # Emit next tool_use event
            tool_name, arguments = next_tool
            tool_use_id = str(uuid_mod.uuid4())[:8]
            arguments_json = json.dumps(arguments)

            yield StreamEvent(messageStart={"role": "assistant"})
            yield StreamEvent(
                contentBlockStart={
                    "start": {"toolUse": {"toolUseId": tool_use_id, "name": tool_name}},
                    "contentBlockIndex": 0,
                }
            )
            yield StreamEvent(
                contentBlockDelta={
                    "delta": {"toolUse": {"input": arguments_json}},
                    "contentBlockIndex": 0,
                }
            )
            yield StreamEvent(contentBlockStop={"contentBlockIndex": 0})
            yield StreamEvent(
                messageStop={"stopReason": "tool_use", "additionalModelResponseFields": None}
            )
        else:
            # All tools done — synthesize a grounded answer from tool results
            synthesis = self._synthesize_answer(tool_results_data, user_question)

            yield StreamEvent(messageStart={"role": "assistant"})
            yield StreamEvent(
                contentBlockStart={"start": {"text": ""}, "contentBlockIndex": 0}
            )
            yield StreamEvent(
                contentBlockDelta={
                    "delta": {"text": synthesis},
                    "contentBlockIndex": 0,
                }
            )
            yield StreamEvent(contentBlockStop={"contentBlockIndex": 0})
            yield StreamEvent(
                messageStop={"stopReason": "end_turn", "additionalModelResponseFields": None}
            )

    def _determine_next_tool(
        self,
        intent,
        completed_tools: list[str],
        tool_results_data: list[dict],
        user_question: str,
        project_id: str,
    ) -> tuple[str, dict] | None:
        """Determine whether another tool call is needed and which one.

        Returns None when all required tools are done (time to synthesize).
        Returns (tool_name, arguments) when another tool call is needed.

        Dataset discovery is conditional:
        - If dataset name can be inferred → query_dataset directly
        - Otherwise → list_available_datasets first
        """
        from app.ai.question_classifier import QuestionIntent

        if intent == QuestionIntent.QUALITATIVE:
            # Qualitative: only search_documents needed, then synthesize
            return None

        elif intent == QuestionIntent.QUANTITATIVE:
            if "query_dataset" in completed_tools:
                # Done — synthesize
                return None
            elif "list_available_datasets" in completed_tools:
                # We did discovery, now query the dataset
                dataset_id = self._find_dataset_id_from_results(tool_results_data)
                return ("query_dataset", {"dataset_id": dataset_id, "query_params": {}})
            else:
                # Check if we can infer the dataset name directly
                inferred_dataset = self._classifier.infer_dataset_name(user_question)
                if inferred_dataset:
                    # Skip discovery — query directly with a well-known name
                    # NOTE: We use the inferred name as dataset_id; the tool will
                    # need to resolve it. In demo mode with seeded data, this works.
                    return ("query_dataset", {"dataset_id": inferred_dataset, "query_params": {}})
                else:
                    return ("list_available_datasets", {"project_id": project_id})

        elif intent == QuestionIntent.HYBRID:
            if "search_documents" not in completed_tools:
                # This shouldn't happen in normal flow (search_documents is first)
                search_query = self._derive_search_query(user_question)
                return ("search_documents", {"project_id": project_id, "query": search_query})

            # search_documents is done — now we need structured data
            if "query_dataset" in completed_tools:
                # Both done — synthesize
                return None
            elif "list_available_datasets" in completed_tools:
                # Discovery done — now query the dataset
                dataset_id = self._find_dataset_id_from_results(tool_results_data)
                return ("query_dataset", {"dataset_id": dataset_id, "query_params": {}})
            else:
                # Need structured data — check if we can infer dataset
                inferred_dataset = self._classifier.infer_dataset_name(user_question)
                if inferred_dataset:
                    return ("query_dataset", {"dataset_id": inferred_dataset, "query_params": {}})
                else:
                    return ("list_available_datasets", {"project_id": project_id})

        return None

    def _find_dataset_id_from_results(self, tool_results_data: list[dict]) -> str:
        """Extract a dataset_id from list_available_datasets results.

        Looks for the first dataset in the discovery results and returns its ID.
        Falls back to a placeholder if no datasets found.
        """
        for result in tool_results_data:
            datasets = result.get("datasets", [])
            if datasets and isinstance(datasets, list):
                first_dataset = datasets[0]
                if isinstance(first_dataset, dict):
                    return str(first_dataset.get("id", first_dataset.get("dataset_id", "")))
        return ""

    def _get_completed_tools(self, messages: list) -> list[str]:
        """Extract the list of tool names that have already been called.

        Inspects assistant messages for toolUse blocks to determine which
        tools have been invoked in this conversation.
        """
        completed: list[str] = []
        for msg in messages or []:
            if not isinstance(msg, dict):
                continue
            if msg.get("role") == "assistant":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and "toolUse" in block:
                            tool_use = block["toolUse"]
                            if isinstance(tool_use, dict) and "name" in tool_use:
                                completed.append(tool_use["name"])
        return completed

    def _extract_all_tool_result_data(self, messages: list) -> list[dict]:
        """Extract structured data from all tool result messages.

        Parses tool_result content (JSON) to recover the full dict returned
        by @tool functions, for use in synthesis.
        """
        import json

        results: list[dict] = []
        for msg in messages or []:
            if not isinstance(msg, dict):
                continue
            # Format 1: role="tool" messages
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                parsed = self._try_parse_json(content)
                if parsed:
                    results.append(parsed)
            # Format 2: toolResult content blocks in user messages
            elif msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and "toolResult" in block:
                            tr = block["toolResult"]
                            tr_content = tr.get("content", [])
                            text = self._extract_text_from_blocks(tr_content)
                            parsed = self._try_parse_json(text)
                            if parsed:
                                results.append(parsed)
        return results

    def _extract_first_user_question(self, messages: list | None) -> str:
        """Extract the FIRST user question (with project context) from messages.

        Unlike _extract_user_question which gets the LAST user message,
        this gets the first one containing the contextualized prompt.
        """
        for msg in messages or []:
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("text"):
                            text = block["text"]
                            if "Project context" in text or "User question" in text:
                                return text
                elif isinstance(content, str) and "Project context" in content:
                    return content
        # Fallback to the last user question
        return self._extract_user_question(messages)

    def _extract_text_from_blocks(self, content) -> str:
        """Extract text from content blocks (list of dicts with text keys)."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            return " ".join(parts)
        return str(content) if content else ""

    def _try_parse_json(self, text) -> dict | None:
        """Attempt to parse text as JSON, returning None on failure."""
        import json

        if isinstance(text, dict):
            return text
        if not isinstance(text, str):
            return None
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _synthesize_answer(self, tool_results_data: list[dict], user_question: str) -> str:
        """Synthesize a grounded answer from actual tool results.

        Constructs a narrative that references specific evidence from the tools:
        file names, excerpts, metric values, dataset names. Never fabricates data.

        Args:
            tool_results_data: Parsed dicts from each tool's response.
            user_question: The original user question for context.

        Returns:
            A synthesis text grounded in tool results.
        """
        doc_evidence: list[str] = []
        data_evidence: list[str] = []
        failed_sources: list[str] = []

        for result in tool_results_data:
            # Handle search_documents results
            if "results" in result and result.get("source_type") == "document":
                search_results = result.get("results", [])
                for item in search_results:
                    if isinstance(item, dict):
                        file_name = item.get("file_name", "")
                        excerpt = item.get("excerpt", "")
                        section = item.get("section", "")
                        if excerpt:
                            citation = f"According to {file_name}"
                            if section:
                                citation += f", {section}"
                            citation += f": \"{excerpt[:200]}\""
                            doc_evidence.append(citation)

            # Handle query_dataset results
            elif "records" in result and result.get("source_type") == "structured":
                records = result.get("records", [])
                aggregations = result.get("aggregations", {})
                dataset_label = result.get("source_label", "Structured data")

                if aggregations:
                    for key, value in aggregations.items():
                        data_evidence.append(
                            f"The dataset shows {key}: {value}"
                        )
                elif records:
                    # Summarize key metrics from first few records
                    for record in records[:3]:
                        if isinstance(record, dict):
                            parts = [
                                f"{k}: {v}" for k, v in record.items()
                                if v is not None and k not in ("id", "project_id")
                            ]
                            if parts:
                                data_evidence.append(f"{dataset_label} indicates {', '.join(parts[:4])}")

            # Handle list_available_datasets
            elif "datasets" in result:
                # This is informational — don't add to evidence narrative
                pass

            # Handle errors
            elif "error" in result:
                source = result.get("source_label", "Unknown source")
                failed_sources.append(source)

        # Build the synthesis
        parts: list[str] = []

        if doc_evidence:
            parts.append("Based on the available documentation:\n\n")
            parts.append("\n\n".join(doc_evidence[:5]))

        if data_evidence:
            if parts:
                parts.append("\n\nSupporting data from structured sources:\n\n")
            else:
                parts.append("Based on available structured data:\n\n")
            parts.append("\n\n".join(data_evidence[:5]))

        if failed_sources:
            parts.append(
                f"\n\nNote: Some sources ({', '.join(failed_sources)}) "
                "were unavailable and could not be consulted."
            )

        if not parts:
            # No evidence found — acknowledge the limitation
            return (
                "Based on available data, I could not find sufficient information "
                "to fully answer your question. The enterprise documents and datasets "
                "accessible to me did not contain relevant evidence for this query."
            )

        return "".join(parts)

    def _has_tool_results(self, messages: list | None) -> bool:
        """Check if any tool_result messages are present in the conversation.

        Returns True if tool results exist, indicating this is a continuation call.
        """
        for msg in messages or []:
            if isinstance(msg, dict) and msg.get("role") == "tool":
                return True
            # Strands also uses content blocks with toolResult
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and "toolResult" in block:
                            return True
        return False

    def _extract_user_question(self, messages: list | None) -> str:
        """Extract the user question text from the last user message."""
        for msg in reversed(messages or []):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("text"):
                            return block["text"]
                elif isinstance(content, str):
                    return content
                break
        return ""

    def _extract_project_id(self, text: str) -> str:
        """Extract project_id UUID from the contextualized prompt format.

        Expected format: "Project context — Project ID: {uuid}"
        Falls back to empty string if not found.
        """
        import re

        pattern = r"Project ID:\s*([0-9a-fA-F\-]{36})"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return ""

    def _derive_search_query(self, text: str) -> str:
        """Derive a meaningful search query from the user question.

        Strips the "Project context" prefix and extracts the core question.
        """
        # Remove the contextualized prompt prefix
        if "User question:" in text:
            query = text.split("User question:", 1)[1].strip()
        elif "Project context" in text:
            # Strip everything up to the double newline after context
            parts = text.split("\n\n", 1)
            query = parts[1].strip() if len(parts) > 1 else text
        else:
            query = text

        return query if query else text

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        """Not supported in mock mode."""
        raise NotImplementedError("Structured output not supported in mock mode")
