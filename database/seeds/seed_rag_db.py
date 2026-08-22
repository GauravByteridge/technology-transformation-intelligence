"""
Idempotent seed script for RAG_DB demo data.

Inserts deterministic demo data: documents, document_chunks, and embeddings
with placeholder vectors. Uses fixed UUIDs and a seeded PRNG so repeated
runs produce identical state.

Placeholder embeddings are generated using a seeded random.Random(42) instance.
Each vector is exactly EMBEDDING_DIMENSION floats long (default 1536), and
the same seed always produces the same vectors.

Usage:
    python -m database.seeds.seed_rag_db

Requires RAG_DB_URL environment variable (synchronous driver format):
    postgresql://postgres:postgres@localhost:5432/rag_db

Validates: Requirements 4.5, 14.2
"""

import os
import random
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))
EMBEDDING_MODEL_NAME = "demo-placeholder-v1"

# Seeded PRNG for deterministic placeholder embeddings
_PRNG = random.Random(42)

# ---------------------------------------------------------------------------
# Fixed UUIDs — deterministic across all runs
# ---------------------------------------------------------------------------

# Documents
DOC_MEETING_TRANSCRIPT_ID = "f6a7b8c9-0006-4000-8000-000000000001"
DOC_REQUIREMENTS_ID = "f6a7b8c9-0006-4000-8000-000000000002"

# Chunks — 2 per document
CHUNK_MEETING_1_ID = "a7b8c9d0-0007-4000-8000-000000000001"
CHUNK_MEETING_2_ID = "a7b8c9d0-0007-4000-8000-000000000002"
CHUNK_REQUIREMENTS_1_ID = "a7b8c9d0-0007-4000-8000-000000000003"
CHUNK_REQUIREMENTS_2_ID = "a7b8c9d0-0007-4000-8000-000000000004"

# Embeddings — one per chunk
EMB_MEETING_1_ID = "b8c9d0e1-0008-4000-8000-000000000001"
EMB_MEETING_2_ID = "b8c9d0e1-0008-4000-8000-000000000002"
EMB_REQUIREMENTS_1_ID = "b8c9d0e1-0008-4000-8000-000000000003"
EMB_REQUIREMENTS_2_ID = "b8c9d0e1-0008-4000-8000-000000000004"

# Reference project/user IDs from App_DB seeds
PROJECT_ALPHA_ID = "b2c3d4e5-0002-4000-8000-000000000001"
USER_ADMIN_ID = "a1b2c3d4-0001-4000-8000-000000000001"

SEED_TIMESTAMP = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


def get_rag_db_url() -> str:
    """
    Resolve the RAG_DB connection URL from environment.

    Converts asyncpg URLs to synchronous psycopg2 format for seed scripts.
    """
    url = os.environ.get("RAG_DB_URL", "postgresql://postgres:postgres@localhost:5432/rag_db")
    return url.replace("postgresql+asyncpg://", "postgresql://")


def generate_placeholder_embedding() -> str:
    """
    Generate a deterministic placeholder embedding vector.

    Uses the module-level seeded PRNG so that calling this function
    in the same order always produces the same vectors. Returns a
    PostgreSQL-compatible vector literal string: '[0.1, 0.2, ...]'.
    """
    vector = [_PRNG.uniform(-1.0, 1.0) for _ in range(EMBEDDING_DIMENSION)]
    return "[" + ",".join(f"{v:.8f}" for v in vector) + "]"


def seed_documents(conn) -> None:
    """Insert demo documents."""
    conn.execute(
        text("""
            INSERT INTO documents (
                id, project_id, source_id, file_name, file_type, file_size,
                processing_status, processing_error, uploaded_by, uploaded_at,
                created_at, updated_at
            )
            VALUES
                (:id1, :proj, NULL, :fname1, :ftype1, :fsize1, :status1, NULL, :uploader, :ts, :ts, :ts),
                (:id2, :proj, NULL, :fname2, :ftype2, :fsize2, :status2, NULL, :uploader, :ts, :ts, :ts)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id1": DOC_MEETING_TRANSCRIPT_ID,
            "id2": DOC_REQUIREMENTS_ID,
            "proj": PROJECT_ALPHA_ID,
            "fname1": "2024-01-10_project_alpha_kickoff_meeting.txt",
            "ftype1": "txt",
            "fsize1": 15360,
            "status1": "completed",
            "fname2": "alpha_transformation_requirements_v2.docx",
            "ftype2": "docx",
            "fsize2": 48128,
            "status2": "completed",
            "uploader": USER_ADMIN_ID,
            "ts": SEED_TIMESTAMP,
        },
    )


def seed_document_chunks(conn) -> None:
    """Insert demo chunks with positional metadata."""
    conn.execute(
        text("""
            INSERT INTO document_chunks (id, document_id, chunk_index, content, page_number, section, created_at, updated_at)
            VALUES
                (:id1, :doc1, :idx1, :content1, :page1, :section1, :ts, :ts),
                (:id2, :doc1, :idx2, :content2, :page2, :section2, :ts, :ts),
                (:id3, :doc2, :idx3, :content3, :page3, :section3, :ts, :ts),
                (:id4, :doc2, :idx4, :content4, :page4, :section4, :ts, :ts)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id1": CHUNK_MEETING_1_ID,
            "doc1": DOC_MEETING_TRANSCRIPT_ID,
            "idx1": 0,
            "content1": (
                "Project Alpha kickoff meeting held on January 10, 2024. "
                "Attendees discussed the migration timeline for the core banking platform. "
                "Key risks identified include legacy system dependencies and data migration complexity. "
                "Budget allocation of $2.4M approved for Phase 1."
            ),
            "page1": 1,
            "section1": "Meeting Overview",
            "id2": CHUNK_MEETING_2_ID,
            "idx2": 1,
            "content2": (
                "Action items from the kickoff: (1) Complete technical assessment by Feb 15, "
                "(2) Identify critical integration points with downstream systems, "
                "(3) Draft resource allocation plan for Q1-Q2, "
                "(4) Schedule weekly steering committee reviews starting January 20."
            ),
            "page2": 2,
            "section2": "Action Items",
            "id3": CHUNK_REQUIREMENTS_1_ID,
            "doc2": DOC_REQUIREMENTS_ID,
            "idx3": 0,
            "content3": (
                "The Alpha Transformation project shall modernize the core banking platform "
                "from mainframe-based COBOL systems to a cloud-native microservices architecture. "
                "Non-functional requirements include 99.99% uptime SLA, sub-200ms API response times, "
                "and support for 10x current transaction volumes."
            ),
            "page3": 1,
            "section3": "Executive Summary",
            "id4": CHUNK_REQUIREMENTS_2_ID,
            "idx4": 1,
            "content4": (
                "Security requirements mandate SOC2 Type II compliance, end-to-end encryption "
                "for all data in transit, and role-based access control with audit logging. "
                "The modernized platform must integrate with existing identity providers "
                "and support multi-factor authentication for all administrative operations."
            ),
            "page4": 3,
            "section4": "Security Requirements",
            "ts": SEED_TIMESTAMP,
        },
    )


def seed_embeddings(conn) -> None:
    """
    Insert placeholder embeddings for each chunk.

    Vectors are generated using a seeded PRNG for determinism.
    The PRNG is reset at module load, so calling this function in the
    expected order always produces identical vectors.
    """
    # Generate embeddings in fixed order for reproducibility
    emb_meeting_1 = generate_placeholder_embedding()
    emb_meeting_2 = generate_placeholder_embedding()
    emb_requirements_1 = generate_placeholder_embedding()
    emb_requirements_2 = generate_placeholder_embedding()

    conn.execute(
        text("""
            INSERT INTO embeddings (id, chunk_id, embedding, model_name, dimension, created_at, updated_at)
            VALUES
                (:id1, :chunk1, :emb1::vector, :model, :dim, :ts, :ts),
                (:id2, :chunk2, :emb2::vector, :model, :dim, :ts, :ts),
                (:id3, :chunk3, :emb3::vector, :model, :dim, :ts, :ts),
                (:id4, :chunk4, :emb4::vector, :model, :dim, :ts, :ts)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id1": EMB_MEETING_1_ID,
            "chunk1": CHUNK_MEETING_1_ID,
            "emb1": emb_meeting_1,
            "id2": EMB_MEETING_2_ID,
            "chunk2": CHUNK_MEETING_2_ID,
            "emb2": emb_meeting_2,
            "id3": EMB_REQUIREMENTS_1_ID,
            "chunk3": CHUNK_REQUIREMENTS_1_ID,
            "emb3": emb_requirements_1,
            "id4": EMB_REQUIREMENTS_2_ID,
            "chunk4": CHUNK_REQUIREMENTS_2_ID,
            "emb4": emb_requirements_2,
            "model": EMBEDDING_MODEL_NAME,
            "dim": EMBEDDING_DIMENSION,
            "ts": SEED_TIMESTAMP,
        },
    )


def seed_rag_db() -> None:
    """Run all RAG_DB seed operations in a single transaction."""
    db_url = get_rag_db_url()
    engine = create_engine(db_url)

    with engine.begin() as conn:
        seed_documents(conn)
        seed_document_chunks(conn)
        seed_embeddings(conn)

    engine.dispose()
    print("RAG_DB seed completed successfully.")


if __name__ == "__main__":
    seed_rag_db()
