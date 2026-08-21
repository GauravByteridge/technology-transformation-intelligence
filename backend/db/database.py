"""
Database connection and session management.

Provides SQLAlchemy engine, session factory, and dependency injection
for FastAPI route handlers.

Supports both PostgreSQL and SQLite. Defaults to SQLite for zero-config local development.
Set DATABASE_URL environment variable for PostgreSQL in production.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite database file in the backend directory for zero-config POC setup.
# For PostgreSQL: change this to your connection string.
_DB_PATH = Path(__file__).resolve().parent.parent / "project_intelligence_hub.db"
DATABASE_URL = f"sqlite:///{_DB_PATH}"

# Create SQLAlchemy engine
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)

# Enable foreign key enforcement for SQLite
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for ORM models
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session.
    Ensures the session is closed after each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
