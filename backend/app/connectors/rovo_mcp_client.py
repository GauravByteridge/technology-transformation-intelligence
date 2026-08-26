"""
Atlassian Rovo MCP Client — connects to Atlassian's cloud MCP server.

Provides access to Jira, Confluence, and other Atlassian tools via the
Model Context Protocol (MCP) over Streamable HTTP transport.

Authentication: Basic auth (email:api_token) per Atlassian's API token flow.
Endpoint: https://mcp.atlassian.com/v1/mcp

Security: API token is resolved from settings at runtime. Never logged or returned.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)

ROVO_MCP_URL = "https://mcp.atlassian.com/v1/mcp"


class RovoMCPClient:
    """Client for the Atlassian Rovo MCP Server.

    Connects to the remote Atlassian MCP server using Basic auth and
    exposes tool listing and calling capabilities.

    Usage:
        client = RovoMCPClient(email="user@example.com", api_token="...")
        tools = await client.list_tools()
        result = await client.call_tool("jira_search_issues", {"jql": "..."})
    """

    def __init__(self, email: str, api_token: str, url: str | None = None, cloud_id: str | None = None) -> None:
        """Initialize with Atlassian credentials.

        Args:
            email: Atlassian account email.
            api_token: Personal API token with MCP scopes.
            url: Optional override for MCP server URL (default: Atlassian cloud).
            cloud_id: Optional cloudId for the Atlassian site. Auto-discovered if not set.
        """
        self._email = email
        self._api_token = api_token
        self._url = url or ROVO_MCP_URL
        self._cloud_id = cloud_id
        self._auth_header = self._build_auth_header()

    def _build_auth_header(self) -> str:
        """Build Basic auth header from email:api_token."""
        credentials = f"{self._email}:{self._api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools from the Rovo MCP server.

        Returns:
            List of tool definitions with name, description, and input_schema.
        """
        headers = {"Authorization": self._auth_header}

        async with streamablehttp_client(self._url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()

                tools = []
                for tool in result.tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
                    })

                logger.info("rovo_mcp_list_tools", extra={"tool_count": len(tools)})
                return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the Rovo MCP server.

        Args:
            tool_name: Name of the tool to invoke (e.g., "jira_search_issues").
            arguments: Tool arguments matching its input schema.

        Returns:
            Dict with "content" (list of text/image blocks), "is_error" flag,
            and "structured_content" if available.
        """
        headers = {"Authorization": self._auth_header}

        async with streamablehttp_client(self._url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

                # Extract text content from the result
                content_blocks = []
                for block in result.content:
                    if hasattr(block, "text"):
                        content_blocks.append({"type": "text", "text": block.text})
                    elif hasattr(block, "data"):
                        content_blocks.append({"type": "image", "data": block.data})

                response = {
                    "content": content_blocks,
                    "is_error": result.isError if hasattr(result, "isError") else False,
                }

                # Add structured content if available
                if hasattr(result, "structuredContent") and result.structuredContent:
                    response["structured_content"] = result.structuredContent

                logger.info(
                    "rovo_mcp_call_tool",
                    extra={
                        "tool_name": tool_name,
                        "is_error": response["is_error"],
                        "content_blocks": len(content_blocks),
                    },
                )
                return response

    async def _ensure_cloud_id(self) -> str:
        """Get the cloudId, auto-discovering from Atlassian if not set."""
        if self._cloud_id:
            return self._cloud_id

        # Discover from getAccessibleAtlassianResources
        result = await self.call_tool("getAccessibleAtlassianResources", {})
        if not result.get("is_error"):
            import json
            for block in result.get("content", []):
                if block.get("type") == "text":
                    try:
                        resources = json.loads(block["text"])
                        if resources and isinstance(resources, list):
                            self._cloud_id = resources[0]["id"]
                            logger.info("rovo_mcp_cloud_id_discovered", extra={"cloud_id": self._cloud_id})
                            return self._cloud_id
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass

        raise RuntimeError("Could not discover Atlassian cloudId")

    async def search_jira_issues(self, jql: str, max_results: int = 20) -> dict[str, Any]:
        """Convenience: search Jira issues via JQL.

        Uses searchJiraIssuesUsingJql if available (requires scoped token).

        Args:
            jql: JQL query string.
            max_results: Maximum results to return.

        Returns:
            Tool result with issue data.
        """
        cloud_id = await self._ensure_cloud_id()
        return await self.call_tool("searchJiraIssuesUsingJql", {
            "cloudId": cloud_id,
            "jql": jql,
            "maxResults": max_results,
        })

    async def get_jira_issue(self, issue_key: str) -> dict[str, Any]:
        """Convenience: get a specific Jira issue.

        Uses getJiraIssue if available (requires scoped token).

        Args:
            issue_key: Issue key (e.g., "SCRUM-101").

        Returns:
            Tool result with issue details.
        """
        cloud_id = await self._ensure_cloud_id()
        return await self.call_tool("getJiraIssue", {
            "cloudId": cloud_id,
            "issueIdOrKey": issue_key,
        })

    async def search_confluence(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Convenience: search Confluence content.

        Uses searchConfluenceUsingCql if available (requires scoped token).

        Args:
            query: Search query (CQL or text).
            limit: Max results.

        Returns:
            Tool result with page data.
        """
        cloud_id = await self._ensure_cloud_id()
        return await self.call_tool("searchConfluenceUsingCql", {
            "cloudId": cloud_id,
            "cql": f'text ~ "{query}"',
            "limit": limit,
        })

    async def get_teamwork_graph_context(
        self,
        cloud_id: str | None,
        object_type: str,
        object_identifier: str,
        detail_level: str = "full",
    ) -> dict[str, Any]:
        """Get connected context from Teamwork Graph for an Atlassian entity.

        Available with any API token (no special scopes needed).

        Args:
            cloud_id: The Atlassian cloudId UUID. Auto-discovered if None.
            object_type: Entity type (e.g., "AtlassianProject", "JiraWorkItem").
            object_identifier: Entity ARI or key.
            detail_level: "summary" or "full".

        Returns:
            Teamwork Graph context data.
        """
        resolved_cloud_id = cloud_id or await self._ensure_cloud_id()
        return await self.call_tool("getTeamworkGraphContext", {
            "cloudId": resolved_cloud_id,
            "objectType": object_type,
            "objectIdentifier": object_identifier,
            "detailLevel": detail_level,
        })
