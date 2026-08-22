"""
Integration test fixtures for repository layer tests.

Uses an in-memory SQLite database via aiosqlite for fast, isolated tests.
Tables are created from AppBase.metadata before each test function and
dropped after it completes, ensuring no shared state between tests.

LIMITATIONS — PostgreSQL vs SQLite:
- SQLite does not support all PostgreSQL types (e.g., native UUID, JSONB, arrays).
  SQLAlchemy's generic types (sa.UUID, sa.JSON) handle this transparently.
- SQLite does not enforce foreign key constraints by default. We enable them via
  the "connect" event so that UNIQUE and FK violations behave as expected.
- SQLite uses `CURRENT_TIMESTAMP` instead of `now()` for server_default. SQLAlchemy
  handles this via sa.func.now() rendering to the appropriate SQL per dialect.
- Some PostgreSQL-specific features (LISTEN/NOTIFY, advisory locks, pg_trgm) are
  untestable with SQLite. Those require a real PostgreSQL instance.
- For full production parity, run tests against a real PostgreSQL container in CI.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import event

from app.models.base import AppBase


@pytest_asyncio.fixture
async def async_session():
    """
    Provide an async SQLite session with all tables created.

    Creates an in-memory SQLite database, creates all AppBase tables,
    yields an AsyncSession for the test, then cleans up.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key enforcement in SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(AppBase.metadata.create_all)

    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(AppBase.metadata.drop_all)

    await engine.dispose()
