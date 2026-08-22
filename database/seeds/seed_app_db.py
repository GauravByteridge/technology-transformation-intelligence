"""
Idempotent seed script for App_DB demo data.

Inserts deterministic demo data: users, projects, project_members,
data_sources, and source_connections. Uses fixed UUIDs so repeated
runs produce the same state (INSERT ... ON CONFLICT DO NOTHING).

Usage:
    python -m database.seeds.seed_app_db

Requires APP_DB_URL environment variable (synchronous driver format):
    postgresql://postgres:postgres@localhost:5432/app_db

Validates: Requirements 4.5, 14.2
"""

import json
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Fixed UUIDs — deterministic across all runs
# ---------------------------------------------------------------------------

USER_ADMIN_ID = "a1b2c3d4-0001-4000-8000-000000000001"
USER_ANALYST_ID = "a1b2c3d4-0001-4000-8000-000000000002"

PROJECT_ALPHA_ID = "b2c3d4e5-0002-4000-8000-000000000001"
PROJECT_BETA_ID = "b2c3d4e5-0002-4000-8000-000000000002"

MEMBER_ADMIN_ALPHA_ID = "c3d4e5f6-0003-4000-8000-000000000001"
MEMBER_ANALYST_ALPHA_ID = "c3d4e5f6-0003-4000-8000-000000000002"
MEMBER_ADMIN_BETA_ID = "c3d4e5f6-0003-4000-8000-000000000003"
MEMBER_ANALYST_BETA_ID = "c3d4e5f6-0003-4000-8000-000000000004"

DATASOURCE_PG_FINANCE_ID = "d4e5f6a7-0004-4000-8000-000000000001"
DATASOURCE_MONGO_RESOURCES_ID = "d4e5f6a7-0004-4000-8000-000000000002"

SOURCE_CONN_ALPHA_FINANCE_ID = "e5f6a7b8-0005-4000-8000-000000000001"
SOURCE_CONN_ALPHA_RESOURCES_ID = "e5f6a7b8-0005-4000-8000-000000000002"
SOURCE_CONN_BETA_FINANCE_ID = "e5f6a7b8-0005-4000-8000-000000000003"
SOURCE_CONN_BETA_RESOURCES_ID = "e5f6a7b8-0005-4000-8000-000000000004"

# Timestamp for all seed records — deterministic
SEED_TIMESTAMP = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


def get_app_db_url() -> str:
    """
    Resolve the App_DB connection URL from environment.

    Converts asyncpg URLs to synchronous psycopg2 format for seed scripts.
    """
    url = os.environ.get("APP_DB_URL", "postgresql://postgres:postgres@localhost:5432/app_db")
    # Seed scripts use synchronous connections
    return url.replace("postgresql+asyncpg://", "postgresql://")


def seed_users(conn) -> None:
    """Insert demo users with ON CONFLICT DO NOTHING for idempotency."""
    conn.execute(
        text("""
            INSERT INTO users (id, email, name, role, created_at, updated_at)
            VALUES
                (:id1, :email1, :name1, :role1, :ts, :ts),
                (:id2, :email2, :name2, :role2, :ts, :ts)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id1": USER_ADMIN_ID,
            "email1": "admin@demo.example.com",
            "name1": "Demo Admin",
            "role1": "admin",
            "id2": USER_ANALYST_ID,
            "email2": "analyst@demo.example.com",
            "name2": "Demo Analyst",
            "role2": "analyst",
            "ts": SEED_TIMESTAMP,
        },
    )


def seed_projects(conn) -> None:
    """Insert demo projects."""
    conn.execute(
        text("""
            INSERT INTO projects (id, name, description, status, created_by, created_at, updated_at)
            VALUES
                (:id1, :name1, :desc1, :status1, :created_by1, :ts, :ts),
                (:id2, :name2, :desc2, :status2, :created_by2, :ts, :ts)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id1": PROJECT_ALPHA_ID,
            "name1": "Alpha Transformation",
            "desc1": "Core banking platform modernization initiative targeting legacy system replacement with cloud-native architecture.",
            "status1": "active",
            "created_by1": USER_ADMIN_ID,
            "id2": PROJECT_BETA_ID,
            "name2": "Beta Modernization",
            "desc2": "Enterprise resource planning system upgrade to improve operational efficiency and reporting capabilities.",
            "status2": "active",
            "created_by2": USER_ADMIN_ID,
            "ts": SEED_TIMESTAMP,
        },
    )


def seed_project_members(conn) -> None:
    """Insert project membership links."""
    conn.execute(
        text("""
            INSERT INTO project_members (id, project_id, user_id, role, created_at, updated_at)
            VALUES
                (:id1, :proj1, :user1, :role1, :ts, :ts),
                (:id2, :proj2, :user2, :role2, :ts, :ts),
                (:id3, :proj3, :user3, :role3, :ts, :ts),
                (:id4, :proj4, :user4, :role4, :ts, :ts)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id1": MEMBER_ADMIN_ALPHA_ID,
            "proj1": PROJECT_ALPHA_ID,
            "user1": USER_ADMIN_ID,
            "role1": "lead",
            "id2": MEMBER_ANALYST_ALPHA_ID,
            "proj2": PROJECT_ALPHA_ID,
            "user2": USER_ANALYST_ID,
            "role2": "analyst",
            "id3": MEMBER_ADMIN_BETA_ID,
            "proj3": PROJECT_BETA_ID,
            "user3": USER_ADMIN_ID,
            "role3": "lead",
            "id4": MEMBER_ANALYST_BETA_ID,
            "proj4": PROJECT_BETA_ID,
            "user4": USER_ANALYST_ID,
            "role4": "analyst",
            "ts": SEED_TIMESTAMP,
        },
    )


def seed_data_sources(conn) -> None:
    """Insert demo external data source configurations."""
    pg_config = json.dumps({
        "host": "localhost",
        "port": 5432,
        "database": "finance_db",
        "username": "readonly_user",
    })
    mongo_config = json.dumps({
        "host": "localhost",
        "port": 27017,
        "database": "resources_db",
        "collection_prefix": "proj_",
    })

    conn.execute(
        text("""
            INSERT INTO data_sources (id, name, source_type, display_label, connection_config, connection_status, created_at, updated_at)
            VALUES
                (:id1, :name1, :type1, :label1, :config1::jsonb, :status1, :ts, :ts),
                (:id2, :name2, :type2, :label2, :config2::jsonb, :status2, :ts, :ts)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id1": DATASOURCE_PG_FINANCE_ID,
            "name1": "Finance PostgreSQL",
            "type1": "postgresql",
            "label1": "Finance Database",
            "config1": pg_config,
            "status1": "connected",
            "id2": DATASOURCE_MONGO_RESOURCES_ID,
            "name2": "Resource MongoDB",
            "type2": "mongodb",
            "label2": "Resource Database",
            "config2": mongo_config,
            "status2": "connected",
            "ts": SEED_TIMESTAMP,
        },
    )


def seed_source_connections(conn) -> None:
    """Link data sources to projects."""
    conn.execute(
        text("""
            INSERT INTO source_connections (id, project_id, data_source_id, purpose, created_at, updated_at)
            VALUES
                (:id1, :proj1, :ds1, :purpose1, :ts, :ts),
                (:id2, :proj2, :ds2, :purpose2, :ts, :ts),
                (:id3, :proj3, :ds3, :purpose3, :ts, :ts),
                (:id4, :proj4, :ds4, :purpose4, :ts, :ts)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id1": SOURCE_CONN_ALPHA_FINANCE_ID,
            "proj1": PROJECT_ALPHA_ID,
            "ds1": DATASOURCE_PG_FINANCE_ID,
            "purpose1": "finance",
            "id2": SOURCE_CONN_ALPHA_RESOURCES_ID,
            "proj2": PROJECT_ALPHA_ID,
            "ds2": DATASOURCE_MONGO_RESOURCES_ID,
            "purpose2": "resources",
            "id3": SOURCE_CONN_BETA_FINANCE_ID,
            "proj3": PROJECT_BETA_ID,
            "ds3": DATASOURCE_PG_FINANCE_ID,
            "purpose3": "finance",
            "id4": SOURCE_CONN_BETA_RESOURCES_ID,
            "proj4": PROJECT_BETA_ID,
            "ds4": DATASOURCE_MONGO_RESOURCES_ID,
            "purpose4": "resources",
            "ts": SEED_TIMESTAMP,
        },
    )


def seed_app_db() -> None:
    """Run all App_DB seed operations in a single transaction."""
    db_url = get_app_db_url()
    engine = create_engine(db_url)

    with engine.begin() as conn:
        seed_users(conn)
        seed_projects(conn)
        seed_project_members(conn)
        seed_data_sources(conn)
        seed_source_connections(conn)

    engine.dispose()
    print("App_DB seed completed successfully.")


if __name__ == "__main__":
    seed_app_db()
