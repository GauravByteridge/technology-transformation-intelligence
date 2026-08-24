"""
AI Tools package.

Contains domain-scoped tool functions invoked by the AI agent.
Tools access data exclusively through domain services — never
through direct database imports or credentials.

Phase 5 adds ingestion tools using the Strands @tool decorator
for LLM-driven tool selection.

Phase 8 adds connector tools for cross-source intelligence:
query_connected_source and discover_available_sources.
"""

from app.ai.tools.registry import ToolRegistry
from app.ai.tools.project_tools import create_get_project_context
from app.ai.tools.finance_tools import create_query_project_finance
from app.ai.tools.ingestion_tools import (
    get_ingestion_tools,
    initialize_ingestion_tools,
)

# NOTE: connector_tools imports are deferred to avoid circular import.
# Use direct imports from app.ai.tools.connector_tools where needed:
#   from app.ai.tools.connector_tools import (
#       create_query_connected_source, create_discover_available_sources,
#       get_connector_tools, initialize_connector_tools,
#   )

__all__ = [
    "ToolRegistry",
    "create_get_project_context",
    "create_query_project_finance",
    "get_ingestion_tools",
    "initialize_ingestion_tools",
]
