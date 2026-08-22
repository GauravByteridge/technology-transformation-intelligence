"""
Alembic environment configuration for App_DB.

Supports both online (connected to database) and offline (SQL script generation)
migration modes using SQLAlchemy 2.0 async engine.

The database URL is loaded from the application settings (APP_DB_URL environment
variable). No credentials are hard-coded in this file.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config.settings import Settings
from app.models.base import AppBase

# Alembic Config object — provides access to alembic.ini values.
config = context.config

# Configure Python logging from the .ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support.
# Import all App_DB models so their tables are registered on AppBase.metadata.
# NOTE: As models are created in later phases, import them in app/models/__init__.py
# so they are registered here automatically.
import app.models  # noqa: F401 — side-effect: registers models on metadata

target_metadata = AppBase.metadata


def get_database_url() -> str:
    """
    Load App_DB URL from application settings.

    Converts asyncpg:// URLs to work with Alembic's sync DDL operations
    by replacing the async driver prefix when needed for offline mode.
    """
    settings = Settings()
    url = settings.app_db_url

    # Alembic needs a URL; ensure it's set.
    if not url:
        raise RuntimeError("APP_DB_URL environment variable is not set")

    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL scripts without a live DB.

    Configures the context with just a URL and not an Engine. Calls to
    context.execute() emit the given string to the script output.
    """
    url = get_database_url()

    # For offline mode, convert async driver to sync equivalent for SQL generation.
    offline_url = url.replace("postgresql+asyncpg://", "postgresql://")

    context.configure(
        url=offline_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations against the provided database connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode using an async engine.

    Creates an async engine from the APP_DB_URL, connects, and runs
    migrations synchronously within the connection context.
    """
    url = get_database_url()

    # Override the sqlalchemy.url in the alembic config with the actual URL.
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — delegates to async runner."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
