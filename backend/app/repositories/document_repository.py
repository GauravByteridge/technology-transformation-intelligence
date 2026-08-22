"""
Document repository — database access layer for RAG_DB document entities.

Handles CRUD operations for documents, chunks, and embeddings.
Vector similarity search interface is defined here but implementation
is deferred to Phase 1.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, Embedding
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """
    Repository for Document entities in RAG_DB.

    Provides document lifecycle operations and defines the interface
    for chunk/embedding storage and similarity search.
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

    async def search_similar(
        self, project_id: UUID, query_vector: list[float], limit: int = 5
    ) -> list[DocumentChunk]:
        """
        Find document chunks most similar to the query vector.

        This method defines the interface for vector similarity search.
        Actual pgvector-based implementation is deferred to Phase 1.

        Args:
            project_id: UUID of the project to scope the search.
            query_vector: The embedding vector to compare against.
            limit: Maximum number of similar chunks to return.

        Returns:
            List of DocumentChunk instances ordered by similarity.

        Raises:
            NotImplementedError: Always — implementation deferred to Phase 1.
        """
        raise NotImplementedError("Vector similarity search deferred to Phase 1")
