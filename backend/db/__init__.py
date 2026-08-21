# Database Module
# Contains database connection, session management, and initialization

from db.database import Base, SessionLocal, engine, get_db
from db.chroma_client import (
    get_chroma_client,
    get_collection,
    add_embeddings,
    query_embeddings,
    delete_embeddings_by_file,
    delete_all_embeddings,
    get_collection_count,
)

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "get_chroma_client",
    "get_collection",
    "add_embeddings",
    "query_embeddings",
    "delete_embeddings_by_file",
    "delete_all_embeddings",
    "get_collection_count",
]
