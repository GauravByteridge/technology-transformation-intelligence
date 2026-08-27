"""
Live Jira Cloud service — fetches issues directly from Jira REST API.

Used by PMO and Project Detail endpoints instead of the dropped jira_issues table.
Reads credentials from environment variables.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (read once at import time from env)
# ---------------------------------------------------------------------------

JIRA_URL = os.getenv("JIRA_URL", "https://byteridge-team-gaurav.atlassian.net")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "gauravs@byteridge.com")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")

# Mapping from internal project_code to Jira project key
# If your Jira project key matches the project_code, this can be 1:1
PROJECT_KEY_MAP: dict[str, str] = {
    "GTBPM": "GTBPM",
    "CMTT": "CMTT",
    "GDP": "GDP",
    "RRRT": "RRRT",
}


@dataclass
class JiraIssue:
    """Flat representation of a Jira issue."""

    issue_key: str
    summary: str
    status: str
    priority: str
    assignee: str | None
    story_points: int | None
    due_date: str | None


def _get_auth() -> httpx.BasicAuth:
    return httpx.BasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)


def _base_url() -> str:
    return JIRA_URL.rstrip("/")


async def fetch_issues_for_project(project_key: str, max_results: int = 50) -> list[JiraIssue]:
    """
    Fetch all issues for a Jira project key via JQL.

    Returns a list of JiraIssue dataclass instances.
    On failure (auth error, network error), returns an empty list.
    """
    jql = f"project = {project_key} ORDER BY priority DESC, created DESC"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{_base_url()}/rest/api/3/search/jql",
                auth=_get_auth(),
                params={
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": "key,summary,status,priority,assignee,customfield_10016,duedate",
                },
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("Jira API call failed for project %s: %s", project_key, str(e)[:200])
        return []

    issues: list[JiraIssue] = []
    for item in data.get("issues", []):
        fields = item.get("fields", {})
        issues.append(JiraIssue(
            issue_key=item.get("key", ""),
            summary=fields.get("summary", ""),
            status=fields.get("status", {}).get("name", "") if fields.get("status") else "",
            priority=fields.get("priority", {}).get("name", "") if fields.get("priority") else "Medium",
            assignee=fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
            story_points=fields.get("customfield_10016"),
            due_date=fields.get("duedate"),
        ))

    return issues


async def count_critical_defects(project_key: str) -> int:
    """Count open Critical-priority issues in a Jira project."""
    jql = f'project = {project_key} AND priority = Critical AND status != Done'
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{_base_url()}/rest/api/3/search/jql",
                auth=_get_auth(),
                params={"jql": jql, "maxResults": 0},
            )
            r.raise_for_status()
            return r.json().get("total", 0)
    except Exception:
        return 0


async def count_open_issues(project_key: str) -> int:
    """Count all non-Done issues in a Jira project."""
    jql = f'project = {project_key} AND status != Done'
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{_base_url()}/rest/api/3/search/jql",
                auth=_get_auth(),
                params={"jql": jql, "maxResults": 0},
            )
            r.raise_for_status()
            return r.json().get("total", 0)
    except Exception:
        return 0


def get_jira_project_key(project_code: str) -> str | None:
    """Map an internal project_code to a Jira project key."""
    return PROJECT_KEY_MAP.get(project_code, project_code)
