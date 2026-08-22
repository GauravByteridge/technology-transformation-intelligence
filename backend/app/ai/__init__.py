"""
AI package — orchestration, agent, tools, providers, and prompts.

Public API:
- AIService: Top-level orchestration entry point
- AIAgent: Agent that invokes tools and synthesizes answers
- ToolRegistry: Registry mapping tool names to async callables
- PromptManager: Loads versioned prompt templates from files
- QueryTrace: Structured trace record for AI query execution
"""

from app.ai.agent import AIAgent
from app.ai.prompt_manager import PromptManager
from app.ai.service import AIService
from app.ai.tools.registry import ToolRegistry
from app.ai.trace import QueryTrace, ToolInvocationTrace

__all__ = [
    "AIAgent",
    "AIService",
    "PromptManager",
    "QueryTrace",
    "ToolInvocationTrace",
    "ToolRegistry",
]
