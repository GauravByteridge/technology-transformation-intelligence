"""
Rovo MCP AI tools — exposes Atlassian Rovo MCP tools to the Strands agent.

Provides the AI with tools to query Jira, Confluence, and other Atlassian
products via the remote Atlassian Rovo MCP server.

The client authenticates with Basic auth (email:api_token) and calls
tools on the Atlassian cloud MCP endpoint.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Any

from strands import tool

logger = logging.getLogger(__name__)

# Module-level state — set during app startup
_rovo_client: Any = None


def initialize_rovo_tools(email: str, api_token: str, url: str | None = None) -> None:
    """Initialize the Rovo MCP client for tool usage.

    Called once during application startup.

    Args:
        email: Atlassian account email.
        api_token: API token for authentication.
        url: Optional MCP server URL override.
    """
    global _rovo_client  # noqa: PLW0603
    from app.connectors.rovo_mcp_client import RovoMCPClient

    _rovo_client = RovoMCPClient(email=email, api_token=api_token, url=url)
    logger.info("rovo_tools_initialized")


def get_rovo_tools() -> list:
    """Return the list of Rovo MCP @tool-decorated functions for Strands.

    Returns empty list if Rovo tools are not initialized (credentials missing).
    """
    if _rovo_client is None:
        return []
    return [
        query_jira_via_rovo,
        get_jira_issue_via_rovo,
        search_confluence_via_rovo,
        get_atlassian_context_via_rovo,
    ]


def _get_client():
    """Get the initialized Rovo MCP client."""
    if _rovo_client is None:
        raise RuntimeError(
            "Rovo tools not initialized. Call initialize_rovo_tools() during startup."
        )
    return _rovo_client


@tool
def query_jira_via_rovo(jql: str, max_results: int = 20) -> dict:
    """Search Jira issues using JQL via Atlassian Rovo MCP.

    Use this for querying Jira issues when you need real-time data from
    Atlassian Cloud. Supports full JQL syntax including project filters,
    status, assignee, labels, sprint, etc.

    Args:
        jql: JQL query string (e.g., "project = SCRUM AND status = 'In Progress'").
        max_results: Maximum number of issues to return (default 20).

    Returns:
        Dict with Jira issue data from the Atlassian cloud, or error info.
    """
    client = _get_client()

    async def _execute() -> dict[str, Any]:
        start = time.monotonic()
        try:
            result = await client.search_jira_issues(jql=jql, max_results=max_results)
            duration_ms = int((time.monotonic() - start) * 1000)

            # Extract text content for the AI
            text_content = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text_content += block.get("text", "")

            is_error = result.get("is_error", False)
            if is_error and "not found" in text_content.lower():
                # Tool not available — fall back gracefully
                return {
                    "error": True,
                    "error_type": "tool_unavailable",
                    "message": "Jira search via Rovo MCP requires a scoped API token. Use query_connected_source with query_type='jira' instead.",
                    "duration_ms": duration_ms,
                }

            return {
                "source": "Atlassian Rovo MCP",
                "tool": "searchJiraIssuesUsingJql",
                "jql": jql,
                "raw_content": text_content,
                "is_error": is_error,
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception("rovo_jira_query_failed", extra={"jql": jql})
            return {
                "error": True,
                "error_type": "rovo_mcp_error",
                "message": f"Rovo MCP query failed: {str(e)[:200]}",
                "duration_ms": duration_ms,
            }

    # Bridge sync @tool to async
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _execute()).result()
        return loop.run_until_complete(_execute())
    except RuntimeError:
        return asyncio.run(_execute())


@tool
def get_jira_issue_via_rovo(issue_key: str) -> dict:
    """Get detailed information about a specific Jira issue via Atlassian Rovo MCP.

    Use this when you need full details of a single issue including description,
    comments, subtasks, linked issues, etc.

    Args:
        issue_key: The Jira issue key (e.g., "SCRUM-101", "ALPHA-1").

    Returns:
        Dict with full issue details from Atlassian cloud.
    """
    client = _get_client()

    async def _execute() -> dict[str, Any]:
        start = time.monotonic()
        try:
            result = await client.get_jira_issue(issue_key=issue_key)
            duration_ms = int((time.monotonic() - start) * 1000)

            text_content = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text_content += block.get("text", "")

            return {
                "source": "Atlassian Rovo MCP",
                "tool": "jira_get_issue",
                "issue_key": issue_key,
                "raw_content": text_content,
                "is_error": result.get("is_error", False),
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception("rovo_get_issue_failed", extra={"issue_key": issue_key})
            return {
                "error": True,
                "error_type": "rovo_mcp_error",
                "message": f"Rovo MCP get issue failed: {str(e)[:200]}",
                "duration_ms": duration_ms,
            }

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _execute()).result()
        return loop.run_until_complete(_execute())
    except RuntimeError:
        return asyncio.run(_execute())


@tool
def search_confluence_via_rovo(query: str, limit: int = 10) -> dict:
    """Search Confluence pages and content via Atlassian Rovo MCP.

    Use this when the user asks about documentation, wiki pages, meeting notes,
    or any content stored in Confluence.

    Args:
        query: Search query (text or CQL expression).
        limit: Maximum results to return (default 10).

    Returns:
        Dict with Confluence page/content results from Atlassian cloud.
    """
    client = _get_client()

    async def _execute() -> dict[str, Any]:
        start = time.monotonic()
        try:
            result = await client.search_confluence(query=query, limit=limit)
            duration_ms = int((time.monotonic() - start) * 1000)

            text_content = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text_content += block.get("text", "")

            return {
                "source": "Atlassian Rovo MCP",
                "tool": "confluence_search",
                "query": query,
                "raw_content": text_content,
                "is_error": result.get("is_error", False),
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception("rovo_confluence_search_failed", extra={"query": query})
            return {
                "error": True,
                "error_type": "rovo_mcp_error",
                "message": f"Rovo MCP Confluence search failed: {str(e)[:200]}",
                "duration_ms": duration_ms,
            }

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _execute()).result()
        return loop.run_until_complete(_execute())
    except RuntimeError:
        return asyncio.run(_execute())


@tool
def get_atlassian_context_via_rovo(object_type: str, object_identifier: str) -> dict:
    """Get connected context from Atlassian Teamwork Graph via Rovo MCP.

    Retrieves relationships and context for any Atlassian entity (project,
    issue, page, etc.) from the Teamwork Graph. Shows how entities connect
    across Jira, Confluence, and other Atlassian products.

    This tool is always available (no special scopes needed).

    Args:
        object_type: Type of entity - "project", "issue", "page", "space", etc.
        object_identifier: The entity's key or ID (e.g., "ALPHA", "SCRUM-101").

    Returns:
        Dict with Teamwork Graph context showing connected entities.
    """
    client = _get_client()

    async def _execute() -> dict[str, Any]:
        start = time.monotonic()
        try:
            # Use the site URL as cloudId
            from app.dependencies import get_settings
            settings = get_settings()
            cloud_id = settings.jira_url or "https://byteridge-team-gaurav.atlassian.net"

            result = await client.get_teamwork_graph_context(
                cloud_id=cloud_id,
                object_type=object_type,
                object_identifier=object_identifier,
            )
            duration_ms = int((time.monotonic() - start) * 1000)

            text_content = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text_content += block.get("text", "")

            return {
                "source": "Atlassian Rovo MCP (Teamwork Graph)",
                "tool": "getTeamworkGraphContext",
                "object_type": object_type,
                "object_identifier": object_identifier,
                "raw_content": text_content,
                "is_error": result.get("is_error", False),
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception("rovo_teamwork_graph_failed", extra={
                "object_type": object_type,
                "object_identifier": object_identifier,
            })
            return {
                "error": True,
                "error_type": "rovo_mcp_error",
                "message": f"Rovo MCP Teamwork Graph query failed: {str(e)[:200]}",
                "duration_ms": duration_ms,
            }

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _execute()).result()
        return loop.run_until_complete(_execute())
    except RuntimeError:
        return asyncio.run(_execute())
