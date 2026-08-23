"""
Document repository — database access layer for RAG_DB document entities.

Handles CRUD operations for documents, chunks, and embeddings.
Provides pgvector cosine similarity search for semantic document retrieval.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, Embedding, EMBEDDING_DIMENSION
from app.repositories.base import BaseRepository


# Maximum allowed results for similarity search
_MAX_SEARCH_LIMIT = 100


class DocumentRepository(BaseRepository[Document]):
    """
    Repository for Document entities in RAG_DB.

    Provides document lifecycle operations, chunk/embedding storage,
    and pgvector cosine similarity search.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Document)

    async def get_document(self, document_id: UUID) -> Document | None:
        """
        Retrieve a document by its primary key.

        Args:
            document_id: UUID of the document to retrieve.

        Returns:
            The Document instance, or None if not found.
        """
        return await self._get_by_id(document_id)

    async def create_document(self, document: Document) -> Document:
        """
        Persist a new document to the database.

        Args:
            document: The Document model instance to persist.

        Returns:
            The persisted Document with generated fields populated.
        """
        return await self._create(document)

    async def list_by_project(self, project_id: UUID) -> list[Document]:
        """
        Retrieve all documents belonging to a specific project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of Document instances for the given project.
        """
        statement = select(Document).where(Document.project_id == project_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        """
        Persist a new document chunk to the database.

        Args:
            chunk: The DocumentChunk model instance to persist.

        Returns:
            The persisted DocumentChunk with generated fields populated.
        """
        self._session.add(chunk)
        await self._session.flush()
        await self._session.refresh(chunk)
        return chunk

    async def create_embedding(self, embedding: Embedding) -> Embedding:
        """
        Persist a new embedding to the database.

        Args:
            embedding: The Embedding model instance to persist.

        Returns:
            The persisted Embedding with generated fields populated.
        """
        self._session.add(embedding)
        await self._session.flush()
        await self._session.refresh(embedding)
        return embedding

    async def delete_document(self, document_id: UUID) -> bool:
        """
        Delete a document by its primary key (cascades to chunks and embeddings).

        Args:
            document_id: UUID of the document to delete.

        Returns:
            True if the document was deleted, False if not found.
        """
        return await self._delete_by_id(document_id)

    async def search_similar(
        self, project_id: UUID, query_vector: list[float], limit: int = 5
    ) -> list[dict]:
        """
        Find document chunks most similar to the query vector using pgvector cosine distance.

        Performs a JOIN from embeddings → document_chunks → documents, filters by
        project_id, and orders by cosine distance ascending (smaller = more similar).

        Args:
            project_id: UUID of the project to scope the search.
            query_vector: The embedding vector to compare against.
            limit: Maximum number of similar chunks to return (default 5, max 100).

        Returns:
            List of dicts with: chunk_content, file_name, page_number, section,
            similarity_score, document_id, chunk_id.

        Raises:
            ValueError: If query_vector dimension doesn't match EMBEDDING_DIMENSION.
        """
        # Validate query vector dimension
        if len(query_vector) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Query vector dimension mismatch: expected {EMBEDDING_DIMENSION}, "
                f"got {len(query_vector)}"
            )

        # Clamp limit to valid range
        effective_limit = max(1, min(limit, _MAX_SEARCH_LIMIT))

        # Compute cosine distance using pgvector operator
        cosine_distance = Embedding.embedding.cosine_distance(query_vector)

        statement = (
            select(
                DocumentChunk.content.label("chunk_content"),
                Document.file_name.label("file_name"),
                DocumentChunk.page_number.label("page_number"),
                DocumentChunk.section.label("section"),
                cosine_distance.label("cosine_distance"),
                Document.id.label("document_id"),
                DocumentChunk.id.label("chunk_id"),
            )
            .select_from(Embedding)
            .join(DocumentChunk, Embedding.chunk_id == DocumentChunk.id)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(Document.project_id == project_id)
            .order_by(cosine_distance.asc())
            .limit(effective_limit)
        )

        result = await self._session.execute(statement)
        rows = result.all()

        return [
            {
                "chunk_content": row.chunk_content,
                "file_name": row.file_name,
                "page_number": row.page_number,
                "section": row.section,
                "similarity_score": round(1.0 - row.cosine_distance, 6),
                "document_id": str(row.document_id),
                "chunk_id": str(row.chunk_id),
            }
            for row in rows
        ]
