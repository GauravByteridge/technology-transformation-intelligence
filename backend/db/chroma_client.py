"""
ChromaDB client initialization and helper functions.

Manages the "project_knowledge" collection for storing document embeddings
used by the RAG pipeline.
"""

import chromadb
from chromadb.config import Settings

# ChromaDB client instance (persistent storage)
_client: chromadb.ClientAPI | None = None
_collection = None

COLLECTION_NAME = "project_knowledge"


def get_chroma_client() -> chromadb.ClientAPI:
    """Get or create the ChromaDB client with persistent storage."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path="./chroma_data")
    return _client


def get_collection():
    """
    Get or create the 'project_knowledge' collection.

    The collection stores document chunks with metadata for RAG retrieval.
    Uses ChromaDB's default embedding function if embeddings are not
    provided explicitly.
    """
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_embeddings(
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> None:
    """
    Add document chunks with embeddings to the collection.

    Args:
        ids: Unique chunk identifiers (format: '{file_id}_{chunk_index}')
        documents: Text content of each chunk
        embeddings: Vector representations for each chunk
        metadatas: Metadata dicts with file_id, file_name, category, chunk_index
    """
    collection = get_collection()
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def query_embeddings(
    query_embedding: list[float],
    n_results: int = 5,
) -> dict:
    """
    Query the collection for the most similar chunks.

    Args:
        query_embedding: Vector representation of the query
        n_results: Number of top results to return (default: 5)

    Returns:
        ChromaDB query result dict with ids, documents, metadatas, distances
    """
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    return results


def delete_embeddings_by_file(file_id: int) -> None:
    """
    Delete all chunk embeddings associated with a specific file.

    Args:
        file_id: The database ID of the file whose chunks should be removed
    """
    collection = get_collection()
    # Query for all chunks belonging to this file
    results = collection.get(
        where={"file_id": file_id},
        include=[],
    )
    if results["ids"]:
        collection.delete(ids=results["ids"])


def delete_all_embeddings() -> None:
    """
    Delete all embeddings from the collection.

    Used during project reset to clear all vector data.
    """
    global _collection
    client = get_chroma_client()
    # Delete and recreate the collection for a clean slate
    client.delete_collection(name=COLLECTION_NAME)
    _collection = None
    # Recreate the empty collection
    get_collection()


def get_collection_count() -> int:
    """
    Get the total number of documents in the collection.

    Returns:
        Number of stored document chunks
    """
    collection = get_collection()
    return collection.count()
