"""Link all existing data sources and catalog entries to the 4 SMBC projects."""
import asyncio
import sys
import os
from uuid import uuid4

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text
from app.config.settings import Settings

PROJECT_IDS = [
    "a1b2c3d4-0002-4000-8000-000000000001",  # GTBPM
    "a1b2c3d4-0002-4000-8000-000000000002",  # CMTT
    "a1b2c3d4-0002-4000-8000-000000000003",  # GDP
    "a1b2c3d4-0002-4000-8000-000000000004",  # RRRT
]


async def main():
    s = Settings()
    e = create_async_engine(s.app_db_url, pool_pre_ping=True)
    f = async_sessionmaker(e, expire_on_commit=False)

    async with f() as session:
        # Get all data sources
        ds_result = await session.execute(text("SELECT id, name, source_type FROM data_sources"))
        data_sources = ds_result.fetchall()
        print(f"Data sources: {len(data_sources)}")
        for ds in data_sources:
            print(f"  {ds[1]} ({ds[2]})")

        # Get all catalog entries
        cat_result = await session.execute(text("SELECT id, source_id, object_name FROM catalog_entries"))
        catalog_entries = cat_result.fetchall()
        print(f"Catalog entries: {len(catalog_entries)}")

        # Clear old mappings
        await session.execute(text("DELETE FROM project_source_mappings"))
        await session.execute(text("DELETE FROM source_connections"))

        # Link all catalog entries to all 4 projects
        mappings_count = 0
        for pid in PROJECT_IDS:
            for cat_id, src_id, obj_name in catalog_entries:
                await session.execute(
                    text("""INSERT INTO project_source_mappings
                            (id, project_id, source_id, catalog_entry_id, project_field, mapping_type, created_at)
                            VALUES (:id, :pid, :sid, :cid, 'project_id', 'configured', now())
                            ON CONFLICT DO NOTHING"""),
                    {"id": str(uuid4()), "pid": pid, "sid": str(src_id), "cid": str(cat_id)}
                )
                mappings_count += 1

            # Source connections
            for ds_id, ds_name, ds_type in data_sources:
                purpose = {
                    "postgresql": "enterprise_data",
                    "mongodb": "qualitative_data",
                    "jira": "issue_tracking",
                }.get(ds_type, "data")
                await session.execute(
                    text("""INSERT INTO source_connections
                            (id, project_id, data_source_id, purpose, created_at, updated_at)
                            VALUES (:id, :pid, :dsid, :purpose, now(), now())
                            ON CONFLICT DO NOTHING"""),
                    {"id": str(uuid4()), "pid": pid, "dsid": str(ds_id), "purpose": purpose}
                )

        await session.commit()
        print(f"\n✓ Created {mappings_count} project-source mappings")
        print(f"✓ All 4 SMBC projects linked to all data sources")

    await e.dispose()


if __name__ == "__main__":
    asyncio.run(main())
