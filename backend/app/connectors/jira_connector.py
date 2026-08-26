"""
Jira Cloud connector implementing the DataSourceConnector protocol.

Provides read-only access to Jira Cloud using the REST API v3.
Discovers projects, issues, and fields. Executes JQL queries.

Security: Uses Basic Auth (email:api_token). Never exposes tokens.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.protocol import (
    FieldInfo,
    QueryResult,
    SchemaInfo,
    SourceMetadata,
    SourceQuery,
    TableSchema,
)
from app.errors.datasource_errors import (
    DataSourceConnectionError,
    QueryExecutionError,
    SchemaDiscoveryError,
)

logger = logging.getLogger(__name__)

_REQUIRED_CONFIG_KEYS = ("url", "email", "api_token")


class JiraConnector:
    """Jira Cloud connector with read-only access via REST API.

    Implements the DataSourceConnector protocol.
    Query format: JQL string (e.g., "project = SCRUM AND status = 'In Progress'")

    Args:
        connection_config: Dict with keys: url, email, api_token, project_key (optional).
        row_limit: Maximum issues returned per query (default 50).
        connection_timeout: Seconds to wait for connection (default 15).
    """

    SOURCE_TYPE = "jira"

    def __init__(
        self,
        connection_config: dict[str, Any],
        *,
        row_limit: int = 50,
        connection_timeout: int = 15,
    ) -> None:
        self._config = connection_config
        self._row_limit = row_limit
        self._timeout = connection_timeout
        self._validate_config()

    def _validate_config(self) -> None:
        missing = [k for k in _REQUIRED_CONFIG_KEYS if k not in self._config]
        if missing:
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Missing required config keys: {', '.join(missing)}",
                detail="operation=validate_config",
            )

    def _get_auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(self._config["email"], self._config["api_token"])

    def _get_base_url(self) -> str:
        return self._config["url"].rstrip("/")

    async def test_connection(self, timeout: int = 10) -> bool:
        """Test connection to Jira Cloud by calling /rest/api/3/myself."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(
                    f"{self._get_base_url()}/rest/api/3/myself",
                    auth=self._get_auth(),
                )
                r.raise_for_status()
                user = r.json()
                logger.info("Jira connection test succeeded", extra={
                    "user": user.get("displayName", "unknown"),
                    "url": self._get_base_url(),
                })
                return True
        except Exception as e:
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Failed to connect to Jira: {str(e)[:200]}",
                detail="operation=test_connection",
            ) from e

    async def discover_metadata(self) -> SourceMetadata:
        """Get Jira server info."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(
                    f"{self._get_base_url()}/rest/api/3/serverInfo",
                    auth=self._get_auth(),
                )
                r.raise_for_status()
                info = r.json()
                return SourceMetadata(
                    source_type=self.SOURCE_TYPE,
                    name=info.get("serverTitle", "Jira Cloud"),
                    version=info.get("version", ""),
                    properties={
                        "baseUrl": info.get("baseUrl", ""),
                        "deploymentType": info.get("deploymentType", ""),
                    },
                )
        except Exception as e:
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Failed to discover Jira metadata: {str(e)[:200]}",
                detail="operation=discover_metadata",
            ) from e

    async def discover_schema(self) -> SchemaInfo:
        """Discover Jira projects and their issue types as 'tables'."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                # Get projects
                r = await client.get(
                    f"{self._get_base_url()}/rest/api/3/project/search",
                    auth=self._get_auth(),
                    params={"maxResults": 50},
                )
                r.raise_for_status()
                projects = r.json().get("values", [])

                tables = []
                # Each project becomes a "table"
                for proj in projects:
                    fields = [
                        FieldInfo(name="key", field_type="string", nullable=False),
                        FieldInfo(name="summary", field_type="string", nullable=False),
                        FieldInfo(name="status", field_type="string", nullable=False),
                        FieldInfo(name="priority", field_type="string", nullable=True),
                        FieldInfo(name="assignee", field_type="string", nullable=True),
                        FieldInfo(name="reporter", field_type="string", nullable=True),
                        FieldInfo(name="issuetype", field_type="string", nullable=False),
                        FieldInfo(name="created", field_type="datetime", nullable=False),
                        FieldInfo(name="updated", field_type="datetime", nullable=False),
                        FieldInfo(name="description", field_type="text", nullable=True),
                        FieldInfo(name="labels", field_type="array", nullable=True),
                        FieldInfo(name="story_points", field_type="number", nullable=True),
                    ]
                    tables.append(TableSchema(
                        name=f"{proj['key']} - {proj['name']}",
                        fields=fields,
                    ))

                return SchemaInfo(tables=tables)
        except Exception as e:
            raise SchemaDiscoveryError(
                source_type=self.SOURCE_TYPE,
                message=f"Failed to discover Jira schema: {str(e)[:200]}",
                detail="operation=discover_schema",
            ) from e

    async def execute_read(self, query: SourceQuery) -> QueryResult:
        """Execute a JQL query against Jira and return issues.

        Args:
            query: JQL string (e.g., "project = SCRUM ORDER BY created DESC")
        """
        if not isinstance(query, str):
            raise QueryExecutionError(
                source_type=self.SOURCE_TYPE,
                message="Jira query must be a JQL string",
            )

        jql = query.strip()
        if not jql:
            jql = f"project = {self._config.get('project_key', 'SCRUM')} ORDER BY created DESC"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(
                    f"{self._get_base_url()}/rest/api/3/search",
                    auth=self._get_auth(),
                    params={
                        "jql": jql,
                        "maxResults": self._row_limit,
                        "fields": "key,summary,status,priority,assignee,reporter,issuetype,created,updated,labels,customfield_10016",
                    },
                )
                r.raise_for_status()
                data = r.json()

                issues = data.get("issues", [])
                rows = []
                for issue in issues:
                    fields = issue.get("fields", {})
                    rows.append({
                        "key": issue.get("key", ""),
                        "summary": fields.get("summary", ""),
                        "status": fields.get("status", {}).get("name", "") if fields.get("status") else "",
                        "priority": fields.get("priority", {}).get("name", "") if fields.get("priority") else "",
                        "assignee": fields.get("assignee", {}).get("displayName", "") if fields.get("assignee") else "Unassigned",
                        "reporter": fields.get("reporter", {}).get("displayName", "") if fields.get("reporter") else "",
                        "issuetype": fields.get("issuetype", {}).get("name", "") if fields.get("issuetype") else "",
                        "created": fields.get("created", "")[:10] if fields.get("created") else "",
                        "updated": fields.get("updated", "")[:10] if fields.get("updated") else "",
                        "labels": ", ".join(fields.get("labels", [])),
                        "story_points": fields.get("customfield_10016"),
                    })

                columns = ["key", "summary", "status", "priority", "assignee", "reporter", "issuetype", "created", "updated", "labels", "story_points"]

                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    source_type=self.SOURCE_TYPE,
                    has_more_rows=data.get("total", 0) > len(rows),
                )

        except httpx.HTTPStatusError as e:
            raise QueryExecutionError(
                source_type=self.SOURCE_TYPE,
                message=f"Jira query failed: {e.response.status_code} - {e.response.text[:200]}",
            ) from e
        except Exception as e:
            raise QueryExecutionError(
                source_type=self.SOURCE_TYPE,
                message=f"Jira query failed: {str(e)[:200]}",
            ) from e
