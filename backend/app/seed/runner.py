"""Seed runner — orchestrates deletion of business domain data and generator invocation.

Workflow:
1. Set random.seed(42) for deterministic field generation
2. Create async DB session via the same engine pattern as the main app
3. Delete all business domain table data (preserving Phase 1 tables)
4. Invoke each generator in dependency order
5. Commit on success
6. On error: rollback all changes, log error with table name and details, exit non-zero
7. Log summary with record counts per table
"""

import random
import sys

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import Settings

logger = structlog.get_logger(__name__)

# Business domain tables to delete in reverse dependency order.
# Phase 1 tables (users, projects, project_members, data_sources, source_connections,
# conversations, messages, query_history, saved_queries, uploaded_files, audit_logs)
# are intentionally excluded to preserve application state.
BUSINESS_DOMAIN_TABLES: list[str] = [
    "project_health_kpis",
    "project_progress_snapshots",
    "project_risks",
    "remediation_items",
    "control_assessments",
    "audit_findings",
    "resource_forecasts",
    "resource_utilization",
    "resource_allocations",
    "jira_issues",
    "sprints",
    "sdlc_deliverables",
    "sdlc_milestones",
    "sdlc_phases",
    "budget_line_items",
    "monthly_cost_trends",
    "actual_costs",
    "project_budgets",
    "cost_categories",
    "team_members",
    "it_controls",
]


def _create_seed_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory for seed operations."""
    engine = create_async_engine(
        settings.app_db_url,
        echo=False,
        pool_pre_ping=True,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


async def _delete_business_domain_data(session: AsyncSession) -> None:
    """Delete all business domain table data in reverse dependency order.

    Preserves Phase 1 application state tables entirely.
    """
    for table_name in BUSINESS_DOMAIN_TABLES:
        await session.execute(text(f"DELETE FROM {table_name}"))  # noqa: S608
        logger.info("table_cleared", table=table_name)


async def run_seed(project_count: int = 10) -> None:
    """Run the full seed pipeline: delete → generate → commit → log summary.

    Args:
        project_count: Number of projects to generate (8–12 range).
    """
    random.seed(42)

    logger.info("seed_started", project_count=project_count)

    settings = Settings()
    session_factory = _create_seed_session_factory(settings)

    async with session_factory() as session:
        try:
            # Step 1: Delete existing business domain data
            await _delete_business_domain_data(session)

            # Step 2: Invoke generators in dependency order
            # NOTE: Generator imports and calls will be added as generators are
            # implemented in subsequent tasks (9.3–9.14). Each generator receives
            # the session and project_count, inserts records, and returns counts.
            record_counts: dict[str, int] = {}

            # TODO: Invoke generators here once implemented:
            # from app.seed.generators import (
            #     generate_projects,
            #     generate_finance,
            #     generate_sdlc,
            #     generate_jira,
            #     generate_resources,
            #     generate_audit,
            #     generate_controls,
            #     generate_remediation,
            #     generate_risks,
            #     generate_progress,
            #     generate_health_kpis,
            # )

            # Step 3: Commit all changes
            await session.commit()

            # Step 4: Log summary
            logger.info(
                "seed_completed",
                project_count=project_count,
                record_counts=record_counts,
            )

        except Exception as exc:
            await session.rollback()
            logger.error(
                "seed_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            sys.exit(1)
