"""Test Rovo MCP connection and tool listing."""
import asyncio
import sys
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.config.settings import Settings
from app.connectors.rovo_mcp_client import RovoMCPClient


async def main():
    s = Settings()
    client = RovoMCPClient(
        email=s.jira_email,
        api_token=s.jira_api_token,
    )

    print("=== Listing Rovo MCP Tools ===")
    try:
        tools = await client.list_tools()
        print(f"Available tools: {len(tools)}")
        for tool in tools:
            desc = tool['description'][:80] if tool['description'] else "No description"
            print(f"  • {tool['name']}")
            print(f"    {desc}")
            if tool.get('input_schema'):
                props = tool['input_schema'].get('properties', {})
                if props:
                    print(f"    Args: {list(props.keys())}")
            print()
    except Exception as e:
        print(f"ERROR listing tools: {e}")
        import traceback
        traceback.print_exc()
        return

    # If Jira tools are available, test them
    tool_names = [t['name'] for t in tools]
    if 'searchJiraIssuesUsingJql' in tool_names:
        print("\n=== Searching Jira Issues (project = ALPHA) ===")
        try:
            result = await client.call_tool("searchJiraIssuesUsingJql", {
                "jql": "project = ALPHA ORDER BY created DESC",
                "maxResults": 10,
            })
            print(f"Error: {result.get('is_error')}")
            for block in result.get("content", []):
                text = block.get("text", "")
                print(f"  Content ({len(text)} chars): {text[:300]}")
        except Exception as e:
            print(f"ERROR: {e}")
    else:
        print("\n⚠ Jira tools not available with current token.")
        print("  To enable Jira/Confluence tools, generate a SCOPED API token at:")
        print("  https://id.atlassian.com/manage-profile/security/api-tokens")
        print("  Required scopes: read:jira-work, read:page:confluence, search:confluence, search:rovo:mcp")

    # Try Teamwork Graph if available
    if 'getTeamworkGraphContext' in tool_names:
        print("\n=== Testing Teamwork Graph ===")
        try:
            # Need to find the cloudId first
            result = await client.call_tool("getTeamworkGraphObject", {
                "cloudId": "https://byteridge-team-gaurav.atlassian.net",
                "objects": [{"objectType": "project", "objectIdentifier": "ALPHA"}],
            })
            print(f"Error: {result.get('is_error')}")
            for block in result.get("content", []):
                text = block.get("text", "")
                print(f"  Content: {text[:300]}")
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
