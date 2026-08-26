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
        api_token=s.rovo_mcp_api_token or s.jira_api_token,
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
        print("\n=== Searching Jira Issues (project = ALPHA) via Rovo MCP ===")
        try:
            result = await client.search_jira_issues("project = ALPHA ORDER BY created DESC", max_results=10)
            print(f"Error: {result.get('is_error')}")
            for block in result.get("content", []):
                text = block.get("text", "")
                print(f"  Content ({len(text)} chars): {text[:500]}")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n⚠ Jira tools not available with current token.")

    # Try Teamwork Graph if available
    if 'getTeamworkGraphContext' in tool_names:
        print("\n=== Testing getAccessibleAtlassianResources ===")
        try:
            result = await client.call_tool("getAccessibleAtlassianResources", {})
            print(f"Error: {result.get('is_error')}")
            for block in result.get("content", []):
                text = block.get("text", "")
                print(f"  Content: {text[:500]}")
        except Exception as e:
            print(f"ERROR: {e}")

        print("\n=== Testing atlassianUserInfo ===")
        try:
            result = await client.call_tool("atlassianUserInfo", {})
            print(f"Error: {result.get('is_error')}")
            for block in result.get("content", []):
                text = block.get("text", "")
                print(f"  Content: {text[:300]}")
        except Exception as e:
            print(f"ERROR: {e}")

        print("\n=== Testing Teamwork Graph with cloudId UUID ===")
        try:
            result = await client.call_tool("getTeamworkGraphContext", {
                "cloudId": "82c91a1e-ce3f-4b9e-8e54-eb2f8712355f",
                "objectType": "AtlassianProject",
                "objectIdentifier": "ALPHA",
                "detailLevel": "full",
            })
            print(f"Error: {result.get('is_error')}")
            for block in result.get("content", []):
                text = block.get("text", "")
                print(f"  Content: {text[:800]}")
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
