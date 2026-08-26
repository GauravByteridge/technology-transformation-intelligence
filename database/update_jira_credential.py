"""Update Jira credential in DB with current token from .env and fix catalog description."""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text
from app.config.settings import Settings
from cryptography.fernet import Fernet


async def main():
    s = Settings()
    e = create_async_engine(s.app_db_url, pool_pre_ping=True)
    f = async_sessionmaker(e, expire_on_commit=False)

    async with f() as session:
        # Get Jira source id
        r = await session.execute(text("SELECT id FROM data_sources WHERE name = 'Jira Cloud'"))
        jira_id = r.scalar()
        if not jira_id:
            print("ERROR: Jira Cloud source not found in data_sources")
            return
        jira_id = str(jira_id)
        print(f"Jira source ID: {jira_id}")

        # 1. Re-encrypt and update credential with new token from .env
        fernet = Fernet(s.fernet_key.encode())
        token = s.jira_api_token or "no-token"
        encrypted = fernet.encrypt(token.encode()).decode()

        result = await session.execute(
            text("UPDATE data_source_credentials SET secret_reference = :ref WHERE data_source_id = :dsid AND credential_type = 'api_token'"),
            {"dsid": jira_id, "ref": f"vault://fernet/{encrypted}"}
        )
        if result.rowcount > 0:
            print(f"  ✓ Credential updated (re-encrypted with current .env token)")
        else:
            print("  ⚠ No existing credential found to update — inserting fresh")
            from uuid import uuid4
            await session.execute(
                text("INSERT INTO data_source_credentials (id, data_source_id, credential_type, secret_reference) VALUES (:id, :dsid, 'api_token', :ref)"),
                {"id": str(uuid4()), "dsid": jira_id, "ref": f"vault://fernet/{encrypted}"}
            )
            print("  ✓ Credential inserted")

        # 2. Update catalog entry semantic_description to mention project key SCRUM
        new_desc = (
            "Live Jira Cloud issue tracker for the SCRUM board. "
            "Use JQL with project = SCRUM (e.g. 'project = SCRUM AND status = \"In Progress\" ORDER BY created DESC'). "
            "Contains sprints, stories, tasks, bugs with real-time status, priority, assignee, and labels."
        )
        result2 = await session.execute(
            text("UPDATE catalog_entries SET semantic_description = :desc WHERE source_id = :sid AND object_name = 'SCRUM Board'"),
            {"sid": jira_id, "desc": new_desc}
        )
        if result2.rowcount > 0:
            print(f"  ✓ Catalog description updated (now mentions project = SCRUM)")
        else:
            print("  ⚠ No catalog entry found for SCRUM Board")

        # 3. Also update connection_config on the data_source to include url and email
        # (The connector needs url, email, api_token in merged config)
        import json
        existing_config = await session.execute(
            text("SELECT connection_config FROM data_sources WHERE id = :id"),
            {"id": jira_id}
        )
        config_row = existing_config.scalar()
        config = config_row if isinstance(config_row, dict) else {}
        config["url"] = s.jira_url or "https://byteridge-team-gaurav.atlassian.net"
        config["email"] = s.jira_email or "gauravs@byteridge.com"
        config["project_key"] = "SCRUM"

        await session.execute(
            text("UPDATE data_sources SET connection_config = cast(:cfg as jsonb) WHERE id = :id"),
            {"id": jira_id, "cfg": json.dumps(config)}
        )
        print(f"  ✓ Connection config updated (url, email, project_key)")

        await session.commit()

    await e.dispose()
    print("\n✅ Jira source fully updated!")


if __name__ == "__main__":
    asyncio.run(main())
