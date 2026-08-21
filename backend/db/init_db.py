"""
Database initialization script.

Creates all tables defined in the SQLAlchemy models if they don't already exist.
Run this script to set up the PostgreSQL database schema.

Usage:
    python -m db.init_db
"""

from db.database import Base, engine

# Import models so they are registered with Base.metadata
from models.database_models import File, Project  # noqa: F401


def init_database():
    """Create all database tables based on the ORM models."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    init_database()
