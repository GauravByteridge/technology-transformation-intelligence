"""
AI Tools package.

Contains domain-scoped tool functions invoked by the AI agent.
Tools access data exclusively through domain services — never
through direct database imports or credentials.
"""

from app.ai.tools.registry import ToolRegistry
from app.ai.tools.project_tools import create_get_project_context
from app.ai.tools.finance_tools import create_query_project_finance

__all__ = [
    "ToolRegistry",
    "create_get_project_context",
    "create_query_project_finance",
]
