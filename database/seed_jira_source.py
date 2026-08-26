"""Seed Jira Cloud as a data source with credentials and catalog entry."""
import asyncio
import sys
import json
from uuid import uuid4
from datetime import datetime, timezone

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, "backend")
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text
from app.config.settings import Settings
from cryptography.fernet import Fernet


async def main():
    s = Settings()
    e = create_async_engine(s.app_db_url, pool_pre_ping=True)
    f = async_sessionmaker(e, expire_on_commit=False)

    async with f() as session:
        # Get jira source id
        r = await session.execute(text("SELECT id FROM data_sources WHERE name = 'Jira Cloud'"))
        jira_id = r.scalar()
        if not jira_id:
            print("Jira Cloud source not found in data_sources")
            return
        jira_id = str(jira_id)
        print(f"Jira source ID: {jira_id}")

        # Store API token as credential
        fernet = Fernet(s.fernet_key.encode())
        token = s.jira_api_token or "no-token"
        encrypted = fernet.encrypt(token.encode()).decode()
        
        # Check if credential already exists
        existing = await session.execute(
            text("SELECT id FROM data_source_credentials WHERE data_source_id = :dsid AND credential_type = 'api_token'"),
            {"dsid": jira_id}
        )
        if not existing.scalar():
            await session.execute(
                text("INSERT INTO data_source_credentials (id, data_source_id, credential_type, secret_reference) VALUES (:id, :dsid, 'api_token', :ref)"),
                {"id": str(uuid4()), "dsid": jira_id, "ref": f"vault://fernet/{encrypted}"}
            )
            print("  ✓ Credential stored")
        else:
            print("  • Credential already exists")

        # Add catalog entry
        existing_cat = await session.execute(
            text("SELECT id FROM catalog_entries WHERE source_id = :sid AND object_name = 'SCRUM Board'"),
            {"sid": jira_id}
        )
        if not existing_cat.scalar():
            now = datetime.now(timezone.utc)
            fields = json.dumps([
                {"name": "key", "field_type": "string", "nullable": False, "is_primary_key": True, "is_sensitive": False, "is_project_field": False, "semantic_label": "Issue Key"},
                {"name": "summary", "field_type": "string", "nullable": False, "is_primary_key": False, "is_sensitive": False, "is_project_field": False, "semantic_label": "Summary"},
                {"name": "status", "field_type": "string", "nullable": False, "is_primary_key": False, "is_sensitive": False, "is_project_field": False, "semantic_label": "Status"},
                {"name": "priority", "field_type": "string", "nullable": True, "is_primary_key": False, "is_sensitive": False, "is_project_field": False, "semantic_label": "Priority"},
                {"name": "assignee", "field_type": "string", "nullable": True, "is_primary_key": False, "is_sensitive": False, "is_project_field": False, "semantic_label": "Assignee"},
                {"name": "issuetype", "field_type": "string", "nullable": False, "is_primary_key": False, "is_sensitive": False, "is_project_field": False, "semantic_label": "Issue Type"},
                {"name": "created", "field_type": "date", "nullable": False, "is_primary_key": False, "is_sensitive": False, "is_project_field": False, "semantic_label": "Created Date"},
                {"name": "labels", "field_type": "array", "nullable": True, "is_primary_key": False, "is_sensitive": False, "is_project_field": False, "semantic_label": "Labels"},
            ])
            await session.execute(
                text("""INSERT INTO catalog_entries (id, source_id, object_name, object_type, fields, primary_keys, foreign_keys, indexes,
                    semantic_name, semantic_description, domain_tags, query_capabilities, suggested_queries, confidence, project_fields, version, discovered_at)
                    VALUES (:id, :sid, :obj, 'board', cast(:fields as jsonb), '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
                    :sname, :sdesc, cast(:domains as jsonb), cast(:caps as jsonb), cast(:queries as jsonb), 'high', '[]'::jsonb, 1, :now)"""),
                {
                    "id": str(uuid4()), "sid": jira_id, "obj": "SCRUM Board",
                    "fields": fields,
                    "sname": "Jira Issues (SCRUM)",
                    "sdesc": "Live Jira Cloud issue tracker — sprints, stories, tasks, bugs with real-time status",
                    "domains": json.dumps(["Delivery", "Engineering", "Project Management"]),
                    "caps": json.dumps(["jql_search", "filter", "status_tracking"]),
                    "queries": json.dumps(["List all Jira issues", "Show open tickets", "What issues are in progress?", "Show the sprint backlog"]),
                    "now": now,
                }
            )
            print("  ✓ Catalog entry added")
        else:
            print("  • Catalog entry already exists")

        # Link to Project Alpha
        existing_mapping = await session.execute(
            text("SELECT id FROM project_source_mappings WHERE source_id = :sid"),
            {"sid": jira_id}
        )
        if not existing_mapping.scalar():
            cat_entry = await session.execute(
                text("SELECT id FROM catalog_entries WHERE source_id = :sid LIMIT 1"),
                {"sid": jira_id}
            )
            cat_id = cat_entry.scalar()
            if cat_id:
                await session.execute(
                    text("INSERT INTO project_source_mappings (id, project_id, source_id, catalog_entry_id, project_field, mapping_type, created_at) VALUES (:id, :pid, :sid, :cid, 'project', 'configured', now())"),
                    {"id": str(uuid4()), "pid": "a1b2c3d4-0002-4000-8000-000000000001", "sid": jira_id, "cid": str(cat_id)}
                )
                print("  ✓ Linked to Project Alpha")
        else:
            print("  • Already linked")

        await session.commit()

    await e.dispose()
    print("\nJira Cloud fully registered as data source!")


if __name__ == "__main__":
    asyncio.run(main())
