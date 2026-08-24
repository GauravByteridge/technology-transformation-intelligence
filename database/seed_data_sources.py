"""
Register PostgreSQL and MongoDB as data sources in the application database,
then run discovery to populate the Enterprise Data Catalog.

This script:
1. Creates a data_source_credentials table if missing
2. Registers 'Client PostgreSQL' as a connected source
3. Registers 'Client MongoDB' as a connected source
4. Stores encrypted credentials
5. Both are linked to Project Alpha

Prerequisites:
- app_db running with migrations applied
- External 'technology_transformation' PostgreSQL database created and seeded
- External MongoDB 'technology_transformation' database created and seeded
- Run: python database/seed_enterprise_sources.py FIRST

Usage:
    python database/seed_data_sources.py
"""

import asyncio
import sys
from uuid import uuid4, UUID
from datetime import datetime, timezone

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text

sys.path.insert(0, "backend")
from app.config.settings import Settings

# Known Project Alpha ID from seed data
PROJECT_ALPHA_ID = UUID("a1b2c3d4-0002-4000-8000-000000000001")
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def main():
    settings = Settings()
    engine = create_async_engine(settings.app_db_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    print("\n" + "=" * 60)
    print("  Registering Enterprise Data Sources")
    print("=" * 60 + "\n")

    async with factory() as session:
        # Ensure data_source_credentials table exists
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS data_source_credentials (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
                credential_type VARCHAR(50) NOT NULL,
                secret_reference VARCHAR(500) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        await session.commit()

    async with factory() as session:
        # Check if sources already exist
        existing = await session.execute(
            text("SELECT name FROM data_sources WHERE name IN ('Client PostgreSQL', 'Client MongoDB')")
        )
        existing_names = {row[0] for row in existing.fetchall()}

        # --- PostgreSQL Source ---
        if 'Client PostgreSQL' not in existing_names:
            pg_id = uuid4()
            await session.execute(text("""
                INSERT INTO data_sources (id, name, source_type, display_label, connection_config, connection_status, discovery_status, objects_discovered, fields_discovered)
                VALUES (:id, :name, :source_type, :label, cast(:config as json), :status, :disc_status, :objects, :fields)
            """), {
                "id": str(pg_id),
                "name": "Client PostgreSQL",
                "source_type": "postgresql",
                "label": "Client PostgreSQL",
                "config": '{"host": "localhost", "port": "5432", "database": "technology_transformation", "user": "postgres"}',
                "status": "connected",
                "disc_status": "completed",
                "objects": 10,
                "fields": 70,
            })

            # Store password credential
            from cryptography.fernet import Fernet
            fernet = Fernet(settings.fernet_key.encode())
            encrypted_pw = fernet.encrypt(b"master").decode()

            await session.execute(text("""
                INSERT INTO data_source_credentials (id, data_source_id, credential_type, secret_reference)
                VALUES (:id, :ds_id, 'password', :ref)
            """), {
                "id": str(uuid4()),
                "ds_id": str(pg_id),
                "ref": f"vault://fernet/{encrypted_pw}",
            })

            print(f"  ✓ Client PostgreSQL registered (ID: {pg_id})")
        else:
            print("  • Client PostgreSQL already exists")
            pg_id = (await session.execute(
                text("SELECT id FROM data_sources WHERE name = 'Client PostgreSQL'")
            )).scalar()

        # --- MongoDB Source ---
        if 'Client MongoDB' not in existing_names:
            mongo_id = uuid4()
            await session.execute(text("""
                INSERT INTO data_sources (id, name, source_type, display_label, connection_config, connection_status, discovery_status, objects_discovered, fields_discovered)
                VALUES (:id, :name, :source_type, :label, cast(:config as json), :status, :disc_status, :objects, :fields)
            """), {
                "id": str(mongo_id),
                "name": "Client MongoDB",
                "source_type": "mongodb",
                "label": "Client MongoDB",
                "config": '{"host": "localhost", "port": "27017", "database": "technology_transformation"}',
                "status": "connected",
                "disc_status": "completed",
                "objects": 4,
                "fields": 25,
            })
            print(f"  ✓ Client MongoDB registered (ID: {mongo_id})")
        else:
            print("  • Client MongoDB already exists")
            mongo_id = (await session.execute(
                text("SELECT id FROM data_sources WHERE name = 'Client MongoDB'")
            )).scalar()

        await session.commit()

    # --- Create source connections to Project Alpha ---
    async with factory() as session:
        # Check existing connections
        existing_conns = await session.execute(text("""
            SELECT data_source_id FROM source_connections WHERE project_id = :pid
        """), {"pid": str(PROJECT_ALPHA_ID)})
        existing_ds_ids = {str(row[0]) for row in existing_conns.fetchall()}

        if str(pg_id) not in existing_ds_ids:
            await session.execute(text("""
                INSERT INTO source_connections (id, project_id, data_source_id, purpose, created_at, updated_at)
                VALUES (:id, :pid, :dsid, :purpose, now(), now())
            """), {
                "id": str(uuid4()),
                "pid": str(PROJECT_ALPHA_ID),
                "dsid": str(pg_id),
                "purpose": "Enterprise financial and project data",
            })
            print(f"  ✓ PostgreSQL linked to Project Alpha")

        if str(mongo_id) not in existing_ds_ids:
            await session.execute(text("""
                INSERT INTO source_connections (id, project_id, data_source_id, purpose, created_at, updated_at)
                VALUES (:id, :pid, :dsid, :purpose, now(), now())
            """), {
                "id": str(uuid4()),
                "pid": str(PROJECT_ALPHA_ID),
                "dsid": str(mongo_id),
                "purpose": "Qualitative risk and project update data",
            })
            print(f"  ✓ MongoDB linked to Project Alpha")

        await session.commit()

    # --- Seed catalog entries ---
    async with factory() as session:
        # Check if catalog already has entries for these sources
        existing_catalog = await session.execute(text("""
            SELECT count(*) FROM catalog_entries WHERE source_id IN (:pg, :mongo)
        """), {"pg": str(pg_id), "mongo": str(mongo_id)})
        count = existing_catalog.scalar()

        if count == 0:
            now = datetime.now(timezone.utc)

            # PostgreSQL catalog entries
            pg_tables = [
                ("projects", "Project registry with codes, status, health, managers, and departments",
                 ["Finance", "Management"], "project_code,name,status,health,manager"),
                ("project_finance", "Project financial data including budget, actual cost, variance",
                 ["Finance"], "budget,actual_cost,variance,variance_percentage"),
                ("project_progress", "Planned vs actual progress tracking",
                 ["Management", "Delivery"], "planned_percent,actual_percent,status_date"),
                ("project_risks_ext", "Structured risk register with severity, status, category",
                 ["Risk"], "severity,status,category,description,owner"),
                ("audit_findings", "Audit findings with severity and remediation status",
                 ["Audit", "Compliance"], "finding_id,severity,status,description"),
                ("remediation_items", "Remediation actions linked to audit findings",
                 ["Audit", "Compliance"], "finding_id,owner,status,due_date"),
                ("it_controls", "IT control compliance assessments",
                 ["Compliance", "Security"], "control_id,control_name,compliance_status"),
                ("resources", "Resource allocation and utilization",
                 ["Resource", "Management"], "employee_name,role,allocation_percent,utilization_percent"),
                ("jira_issues", "JIRA issue tracking with story points",
                 ["Delivery", "Engineering"], "issue_key,summary,status,priority,story_points"),
                ("project_milestones", "Key project milestones and their status",
                 ["Management", "Delivery"], "name,planned_date,actual_date,status"),
            ]

            for table_name, description, domains, key_fields in pg_tables:
                fields = [{"name": f, "field_type": "text", "nullable": True, "is_primary_key": False,
                           "semantic_label": f.replace("_", " ").title(), "is_project_field": f == "project_id",
                           "is_sensitive": False} for f in key_fields.split(",")]
                fields.insert(0, {"name": "id", "field_type": "integer", "nullable": False,
                                  "is_primary_key": True, "is_sensitive": False, "is_project_field": False})
                fields.insert(1, {"name": "project_id", "field_type": "integer", "nullable": False,
                                  "is_primary_key": False, "is_sensitive": False, "is_project_field": True})

                import json
                await session.execute(text("""
                    INSERT INTO catalog_entries (id, source_id, object_name, object_type, fields, primary_keys, foreign_keys, indexes,
                        semantic_name, semantic_description, domain_tags, query_capabilities, suggested_queries, confidence, project_fields, version, discovered_at)
                    VALUES (:id, :sid, :obj, 'table', cast(:fields as jsonb), '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
                        :sname, :sdesc, cast(:domains as jsonb), '["filter", "aggregate", "join"]'::jsonb, cast(:queries as jsonb), 'high', cast(:pf as jsonb), 1, :now)
                """), {
                    "id": str(uuid4()), "sid": str(pg_id), "obj": table_name,
                    "fields": json.dumps(fields),
                    "sname": table_name.replace("_", " ").title(),
                    "sdesc": description,
                    "domains": json.dumps(domains),
                    "queries": json.dumps([f"What is in {table_name}?", f"Show {table_name} data for Project Alpha"]),
                    "pf": json.dumps(["project_id"]),
                    "now": now,
                })

            # MongoDB catalog entries
            mongo_collections = [
                ("project_risks", "Detailed qualitative risk descriptions with impact analysis",
                 ["Risk", "Management"], "severity,status,category,description,impact,owner"),
                ("project_updates", "Weekly project status updates with concerns and decisions",
                 ["Management", "Communication"], "date,author,summary,concerns,decisions"),
                ("project_meeting_observations", "Meeting notes with key observations and action items",
                 ["Management", "Governance"], "meeting_type,attendees,key_observations,action_items"),
                ("project_health_signals", "Automated health signals and trend indicators",
                 ["Analytics", "Management"], "signal_type,description,severity,source"),
            ]

            for coll_name, description, domains, key_fields in mongo_collections:
                fields = [{"name": f, "field_type": "string", "nullable": True, "is_primary_key": False,
                           "semantic_label": f.replace("_", " ").title(), "is_project_field": f == "project_id",
                           "is_sensitive": False} for f in key_fields.split(",")]
                fields.insert(0, {"name": "project_id", "field_type": "string", "nullable": False,
                                  "is_primary_key": False, "is_sensitive": False, "is_project_field": True})

                await session.execute(text("""
                    INSERT INTO catalog_entries (id, source_id, object_name, object_type, fields, primary_keys, foreign_keys, indexes,
                        semantic_name, semantic_description, domain_tags, query_capabilities, suggested_queries, confidence, project_fields, version, discovered_at)
                    VALUES (:id, :sid, :obj, 'collection', cast(:fields as jsonb), '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
                        :sname, :sdesc, cast(:domains as jsonb), '["filter", "aggregate"]'::jsonb, cast(:queries as jsonb), 'high', cast(:pf as jsonb), 1, :now)
                """), {
                    "id": str(uuid4()), "sid": str(mongo_id), "obj": coll_name,
                    "fields": json.dumps(fields),
                    "sname": coll_name.replace("_", " ").title(),
                    "sdesc": description,
                    "domains": json.dumps(domains),
                    "queries": json.dumps([f"What is in {coll_name}?", f"Show {coll_name} for Project Alpha"]),
                    "pf": json.dumps(["project_id"]),
                    "now": now,
                })

            await session.commit()
            print(f"  ✓ Catalog: {len(pg_tables)} PostgreSQL + {len(mongo_collections)} MongoDB entries")
        else:
            print(f"  • Catalog already has {count} entries")

    await engine.dispose()

    print("\n" + "=" * 60)
    print("  Done! Data sources registered and catalog populated.")
    print("")
    print("  PostgreSQL: technology_transformation (localhost:5432)")
    print("  MongoDB: technology_transformation (localhost:27017)")
    print("  Both linked to Project Alpha")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
