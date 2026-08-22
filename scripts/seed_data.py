"""
Main entry point for seeding all demo databases.

Runs both App_DB and RAG_DB seed scripts in sequence.
Idempotent — safe to run multiple times.

Usage:
    python scripts/seed_data.py

Environment variables:
    APP_DB_URL  — App_DB connection (default: postgresql://postgres:postgres@localhost:5432/app_db)
    RAG_DB_URL  — RAG_DB connection (default: postgresql://postgres:postgres@localhost:5432/rag_db)
    EMBEDDING_DIMENSION — Vector dimension for placeholder embeddings (default: 1536)
"""

import sys
from pathlib import Path

# Ensure the project root is on the path so database.seeds can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.seeds.seed_app_db import seed_app_db
from database.seeds.seed_rag_db import seed_rag_db


def main() -> None:
    """Seed both databases with deterministic demo data."""
    print("=" * 60)
    print("Seeding Demo Mode databases...")
    print("=" * 60)

    print("\n[1/2] Seeding App_DB...")
    seed_app_db()

    print("\n[2/2] Seeding RAG_DB...")
    seed_rag_db()

    print("\n" + "=" * 60)
    print("All demo data seeded successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
