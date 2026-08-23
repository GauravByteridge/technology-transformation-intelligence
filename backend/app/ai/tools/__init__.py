"""
AI Tools package.

Contains domain-scoped tool functions invoked by the AI agent.
Tools access data exclusively through domain services — never
through direct database imports or credentials.

Phase 5 adds ingestion tools using the Strands @tool decorator
for LLM-driven tool selection.
"""

from app.ai.tools.registry import ToolRegistry
from app.ai.tools.project_tools import create_get_project_context
from app.ai.tools.finance_tools import create_query_project_finance
from app.ai.tools.ingestion_tools import (
    get_ingestion_tools,
    initialize_ingestion_tools,
)

__all__ = [
    "ToolRegistry",
    "create_get_project_context",
    "create_query_project_finance",
    "get_ingestion_tools",
    "initialize_ingestion_tools",
]
