"""
AI Tool Registry.

A simple dict-based registry mapping tool names to async callable
tool functions. The agent invokes tools by business-intent name
(e.g., "get_project_context", "query_project_finance") without
knowing implementation details of the underlying data source.

Security Invariant:
- Tools registered here MUST NOT accept credentials as parameters.
- Tools MUST NOT import database drivers or ORMs directly.
- Tools access data exclusively through domain service abstractions.
"""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# Type alias for async tool functions
ToolFunction = Callable[..., Coroutine[Any, Any, dict[str, Any]]]


class ToolRegistry:
    """Registry mapping tool names to async callable tool functions.

    Provides a centralized lookup for all AI tools available to the agent.
    Tools are registered by domain name and invoked through business-intent
    identifiers, keeping the agent decoupled from implementation details.

    Example:
        registry = ToolRegistry()
        registry.register("get_project_context", get_project_context_fn)
        tool = registry.get_tool("get_project_context")
        result = await tool(project_id=some_uuid)
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolFunction] = {}

    def register(self, name: str, tool_fn: ToolFunction) -> None:
        """Register a tool function under the given name.

        Args:
            name: Business-intent tool name (e.g., "get_project_context").
            tool_fn: Async callable that performs the tool's operation.

        Raises:
            ValueError: If name is empty or tool_fn is not callable.
        """
        if not name:
            raise ValueError("Tool name must not be empty")
        if not callable(tool_fn):
            raise ValueError(f"Tool function for '{name}' must be callable")

        if name in self._tools:
            logger.warning(
                "tool_registry_overwrite",
                extra={"tool_name": name},
            )

        self._tools[name] = tool_fn
        logger.info(
            "tool_registered",
            extra={"tool_name": name},
        )

    def get_tool(self, name: str) -> ToolFunction:
        """Retrieve a registered tool function by name.

        Args:
            name: The business-intent tool name.

        Returns:
            The async callable tool function.

        Raises:
            KeyError: If no tool is registered under the given name.
        """
        if name not in self._tools:
            available = ", ".join(sorted(self._tools.keys()))
            raise KeyError(
                f"Tool '{name}' not found in registry. "
                f"Available tools: [{available}]"
            )
        return self._tools[name]

    def list_tools(self) -> list[str]:
        """Return a sorted list of all registered tool names.

        Returns:
            Sorted list of tool name strings.
        """
        return sorted(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check whether a tool is registered.

        Args:
            name: The tool name to check.

        Returns:
            True if the tool is registered, False otherwise.
        """
        return name in self._tools

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)
