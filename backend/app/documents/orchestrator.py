"""
Ingestion orchestrator — concrete implementation of the IngestionPipeline protocol.

Chains all pipeline stages together: validate → extract → metadata → chunk →
embed → store. Connects stage outputs to the DocumentRepository for persistence
into RAG_DB.

This is the glue that connects pipeline stages to repository storage.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.documents.pipeline import (
    ChunkResult,
    ContentExtractor,
    DocumentResult,
    EmbeddingGenerator,
    FileValidator,
    MetadataExtractor,
    TextChunker,
)
from app.errors.document_errors import (
    DocumentStorageError,
    EmbeddingGenerationError,
)
from app.models.document import Document, DocumentChunk, Embedding
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """
    Orchestrates the full document ingestion pipeline.

    Implements the IngestionPipeline protocol by chaining all processing
    stages and persisting results through DocumentRepository.

    Each stage is injected as a dependency, allowing different implementations
    (stubs for Phase 0, real extractors in later phases) without changing
    the orchestration logic.
    """

    def __init__(
        self,
        file_validator: FileValidator,
        content_extractor: ContentExtractor,
        metadata_extractor: MetadataExtractor,
        text_chunker: TextChunker,
        embedding_generator: EmbeddingGenerator,
        document_repository: DocumentRepository,
    ) -> None:
        self._file_validator = file_validator
        self._content_extractor = content_extractor
        self._metadata_extractor = metadata_extractor
        self._text_chunker = text_chunker
        self._embedding_generator = embedding_generator
        self._repository = document_repository

    async def ingest(
        self,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size: int,
        project_id: UUID,
        uploaded_by: UUID,
    ) -> DocumentResult:
        """Run the complete ingestion pipeline for a single document.

        Stages executed in order:
        1. Validate file metadata (type, size, format)
        2. Extract text content from the file
        3. Extract metadata from the file and content
        4. Chunk the text into segments with positional info
        5. Generate embeddings for each chunk
        6. Store document, chunks, and embeddings via repository

        Args:
            file_path: Path to the uploaded file on disk.
            file_name: Original file name.
            file_type: MIME type or extension identifier.
            file_size: File size in bytes.
            project_id: Project this document belongs to.
            uploaded_by: UUID of the user who uploaded the file.

        Returns:
            DocumentResult with the stored document ID and chunk count.

        Raises:
            DocumentValidationError: If file validation fails.
            ContentExtractionError: If text extraction fails.
            MetadataExtractionError: If metadata extraction fails.
            ChunkingError: If text chunking fails.
            EmbeddingGenerationError: If embedding generation fails.
            DocumentStorageError: If persisting results to RAG_DB fails.
        """
        logger.info(
            "Starting document ingestion",
            extra={
                "file_name": file_name,
                "file_type": file_type,
                "file_size": file_size,
                "project_id": str(project_id),
            },
        )

        # Stage 1: Validate
        await self._file_validator.validate(file_name, file_type, file_size)
        logger.debug("Validation passed", extra={"file_name": file_name})

        # Stage 2: Extract content
        content = await self._content_extractor.extract(file_path, file_type)
        logger.debug(
            "Content extracted",
            extra={"file_name": file_name, "content_length": len(content)},
        )

        # Stage 3: Extract metadata
        metadata = await self._metadata_extractor.extract_metadata(file_path, content)
        logger.debug(
            "Metadata extracted",
            extra={"file_name": file_name, "metadata_keys": list(metadata.keys())},
        )

        # Stage 4: Chunk text
        chunks: list[ChunkResult] = self._text_chunker.chunk(content)
        logger.debug(
            "Text chunked",
            extra={"file_name": file_name, "chunk_count": len(chunks)},
        )

        # Stage 5: Generate embeddings
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = await self._embedding_generator.generate(chunk_texts)
        logger.debug(
            "Embeddings generated",
            extra={"file_name": file_name, "embedding_count": len(embeddings)},
        )

        # Stage 6: Persist to RAG_DB
        document = await self._store_results(
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            project_id=project_id,
            uploaded_by=uploaded_by,
            chunks=chunks,
            embeddings=embeddings,
        )

        logger.info(
            "Document ingestion completed",
            extra={
                "file_name": file_name,
                "document_id": str(document.id),
                "chunk_count": len(chunks),
            },
        )

        return DocumentResult(
            document_id=document.id,
            chunk_count=len(chunks),
            status="completed",
        )

    async def _store_results(
        self,
        *,
        file_name: str,
        file_type: str,
        file_size: int,
        project_id: UUID,
        uploaded_by: UUID,
        chunks: list[ChunkResult],
        embeddings: list[list[float]],
    ) -> Document:
        """Persist document, chunks, and embeddings via the repository.

        Creates the Document record first, then iterates over chunks and
        their corresponding embeddings, creating chunk and embedding records.

        Args:
            file_name: Original file name.
            file_type: File type identifier.
            file_size: File size in bytes.
            project_id: Owning project UUID.
            uploaded_by: Uploading user UUID.
            chunks: Ordered list of chunking results.
            embeddings: Embedding vectors aligned by index to chunks.

        Returns:
            The persisted Document instance.

        Raises:
            DocumentStorageError: If any database operation fails.
        """
        try:
            # Create document record
            document = Document(
                project_id=str(project_id),
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                uploaded_by=str(uploaded_by),
                processing_status="completed",
            )
            document = await self._repository.create_document(document)

            # Create chunks and embeddings
            for chunk_result, embedding_vector in zip(chunks, embeddings):
                chunk_record = DocumentChunk(
                    document_id=str(document.id),
                    chunk_index=chunk_result.chunk_index,
                    content=chunk_result.text,
                    page_number=chunk_result.page_number,
                    section=chunk_result.section,
                )
                chunk_record = await self._repository.create_chunk(chunk_record)

                embedding_record = Embedding(
                    chunk_id=str(chunk_record.id),
                    embedding=embedding_vector,
                    model_name="deterministic-stub",
                    dimension=len(embedding_vector),
                )
                await self._repository.create_embedding(embedding_record)

            return document

        except Exception as exc:
            # Re-raise domain storage errors as-is
            if isinstance(exc, DocumentStorageError):
                raise
            raise DocumentStorageError(
                file_name=file_name,
                message=f"Failed to store document '{file_name}' in RAG_DB",
                detail=str(exc),
            ) from exc
