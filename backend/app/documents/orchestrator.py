"""
Ingestion orchestrator — concrete implementation of the IngestionPipeline protocol.

Provides two entry points:
- ingest(): Legacy pipeline (validate → extract → metadata → chunk → embed → store)
- process_file(): Content-aware pipeline (detect type → inspect → classify → route per region)

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
from app.models.enums import ProcessingStatus, ProcessingStrategy
from app.processors.content_classifier import ContentClassifier
from app.processors.file_type_detector import FileTypeDetector
from app.processors.protocol import ClassificationResult, DetectedRegion, InspectionResult
from app.processors.registry import FileProcessorRegistry
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """
    Orchestrates the full document ingestion pipeline.

    Implements the IngestionPipeline protocol by chaining all processing
    stages and persisting results through DocumentRepository.

    Supports two modes:
    - ingest(): backward-compatible simple pipeline
    - process_file(): content-aware routing with classification per region
    """

    def __init__(
        self,
        file_validator: FileValidator,
        content_extractor: ContentExtractor,
        metadata_extractor: MetadataExtractor,
        text_chunker: TextChunker,
        embedding_generator: EmbeddingGenerator,
        document_repository: DocumentRepository,
        # Optional dependencies for content-aware processing
        file_type_detector: FileTypeDetector | None = None,
        processor_registry: FileProcessorRegistry | None = None,
        content_classifier: ContentClassifier | None = None,
        dataset_service: object | None = None,
    ) -> None:
        self._file_validator = file_validator
        self._content_extractor = content_extractor
        self._metadata_extractor = metadata_extractor
        self._text_chunker = text_chunker
        self._embedding_generator = embedding_generator
        self._repository = document_repository
        # Content-aware dependencies
        self._file_type_detector = file_type_detector
        self._processor_registry = processor_registry
        self._content_classifier = content_classifier
        self._dataset_service = dataset_service

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

        # Stage 5: Generate embeddings (filter out empty chunks)
        non_empty_chunks = [chunk for chunk in chunks if chunk.text and chunk.text.strip()]
        if non_empty_chunks:
            chunk_texts = [chunk.text for chunk in non_empty_chunks]
            embeddings = await self._embedding_generator.generate(chunk_texts)
        else:
            non_empty_chunks = []
            embeddings = []
        logger.debug(
            "Embeddings generated",
            extra={"file_name": file_name, "embedding_count": len(embeddings), "empty_chunks_skipped": len(chunks) - len(non_empty_chunks)},
        )

        # Stage 6: Persist to RAG_DB
        document = await self._store_results(
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            project_id=project_id,
            uploaded_by=uploaded_by,
            chunks=non_empty_chunks,
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

    async def process_file(
        self,
        file_id: UUID,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size: int,
        project_id: UUID | None,
        uploaded_by: UUID,
    ) -> dict:
        """Content-aware file processing: detect type → inspect → classify → route per region.

        This is the primary entry point for Phase 4 content-aware ingestion.
        Routes each detected region to the appropriate downstream strategy:
        - DATASET_QUERY: create datasets from structured regions
        - RAG: chunk → embed → store in RAG_DB
        - HYBRID: both dataset creation AND RAG indexing
        - IGNORE/REVIEW_REQUIRED: persist the DataRegion only

        Args:
            file_id: UUID of the uploaded file record.
            file_path: Path to the file on disk.
            file_name: Original file name.
            file_type: Extension or MIME type.
            file_size: File size in bytes.
            project_id: Optional project UUID (nullable for unscoped uploads).
            uploaded_by: UUID of the uploading user.

        Returns:
            Dict with processing summary: status, datasets_created, documents_indexed,
            regions_processed, errors.

        Raises:
            RuntimeError: If content-aware dependencies are not configured.
        """
        if not all([
            self._file_type_detector,
            self._processor_registry,
            self._content_classifier,
            self._dataset_service,
        ]):
            raise RuntimeError(
                "Content-aware processing requires file_type_detector, "
                "processor_registry, content_classifier, and dataset_service"
            )

        result = {
            "file_id": str(file_id),
            "file_name": file_name,
            "status": ProcessingStatus.UPLOADED.value,
            "datasets_created": [],
            "documents_indexed": 0,
            "regions_processed": 0,
            "errors": [],
        }

        try:
            # Step 1: Detect file type → get processor_key
            result["status"] = ProcessingStatus.INSPECTING.value
            file_type_result = self._file_type_detector.detect(file_name)
            processor_key = file_type_result.processor_key

            # Step 2: Get the format-specific processor
            processor = self._processor_registry.get_processor(processor_key)

            # Step 3: Inspect file → get regions
            inspection: InspectionResult = await processor.inspect(file_path)

            # Step 4: Classify all regions
            result["status"] = ProcessingStatus.CLASSIFYING.value
            classifications: list[ClassificationResult] = (
                self._content_classifier.classify_batch(inspection.regions)
            )

            # Step 5-8: Route each region to its processing strategy
            result["status"] = ProcessingStatus.NORMALIZING.value

            datasets_created: list[dict] = []
            documents_indexed = 0

            for region, classification in zip(inspection.regions, classifications):
                strategy = classification.processing_strategy
                result["regions_processed"] += 1

                try:
                    if strategy == ProcessingStrategy.DATASET_QUERY.value:
                        # Structured → create dataset only
                        ds_results = await self._create_dataset_for_region(
                            file_id, inspection, region, classification
                        )
                        datasets_created.extend(ds_results)

                    elif strategy == ProcessingStrategy.RAG.value:
                        # Unstructured → RAG pipeline
                        result["status"] = ProcessingStatus.INDEXING.value
                        indexed = await self._index_region_for_rag(
                            file_path, file_name, file_type, file_size,
                            project_id, uploaded_by, region, processor
                        )
                        documents_indexed += indexed

                    elif strategy == ProcessingStrategy.HYBRID.value:
                        # Both dataset AND RAG
                        ds_results = await self._create_dataset_for_region(
                            file_id, inspection, region, classification
                        )
                        datasets_created.extend(ds_results)

                        result["status"] = ProcessingStatus.INDEXING.value
                        indexed = await self._index_region_for_rag(
                            file_path, file_name, file_type, file_size,
                            project_id, uploaded_by, region, processor
                        )
                        documents_indexed += indexed

                    elif strategy in (
                        ProcessingStrategy.IGNORE.value,
                        ProcessingStrategy.REVIEW_REQUIRED.value,
                    ):
                        # Persist region metadata only (handled by dataset_service)
                        await self._persist_region_only(
                            file_id, region, classification
                        )

                except Exception as region_exc:
                    logger.warning(
                        "Region processing failed",
                        extra={
                            "file_id": str(file_id),
                            "region_id": region.region_id,
                            "strategy": strategy,
                            "error": str(region_exc),
                        },
                    )
                    result["errors"].append({
                        "region_id": region.region_id,
                        "strategy": strategy,
                        "error": str(region_exc),
                    })

            result["datasets_created"] = datasets_created
            result["documents_indexed"] = documents_indexed
            result["status"] = ProcessingStatus.READY.value

        except Exception as exc:
            result["status"] = ProcessingStatus.FAILED.value
            result["errors"].append({
                "region_id": None,
                "strategy": None,
                "error": str(exc),
            })
            logger.error(
                "Content-aware file processing failed",
                extra={
                    "file_id": str(file_id),
                    "file_name": file_name,
                    "error": str(exc),
                },
            )

        logger.info(
            "Content-aware file processing completed",
            extra={
                "file_id": str(file_id),
                "status": result["status"],
                "datasets_created": len(result["datasets_created"]),
                "documents_indexed": result["documents_indexed"],
                "regions_processed": result["regions_processed"],
                "error_count": len(result["errors"]),
            },
        )

        return result

    # -------------------------------------------------------------------------
    # Private helpers for process_file()
    # -------------------------------------------------------------------------

    async def _create_dataset_for_region(
        self,
        file_id: UUID,
        inspection: InspectionResult,
        region: DetectedRegion,
        classification: ClassificationResult,
    ) -> list[dict]:
        """Create dataset(s) from a structured/hybrid region via DatasetService.

        Delegates to dataset_service.create_datasets_from_inspection with a
        single-region subset of the inspection.
        """
        # Build a minimal inspection containing only this region
        single_region_inspection = InspectionResult(
            file_name=inspection.file_name,
            file_type=inspection.file_type,
            regions=[region],
            metadata=inspection.metadata,
        )
        return await self._dataset_service.create_datasets_from_inspection(
            file_id=file_id,
            inspection=single_region_inspection,
            classifications=[classification],
        )

    async def _index_region_for_rag(
        self,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size: int,
        project_id: UUID | None,
        uploaded_by: UUID,
        region: DetectedRegion,
        processor: object,
    ) -> int:
        """Extract text from a region and run through chunking → embedding → storage.

        For Excel regions, uses processor.extract_text(). For other file types,
        uses the region's raw_text field.

        Returns:
            Number of chunks indexed (0 if no content).
        """
        # Extract text content from the region
        text_content: str | None = None

        if hasattr(processor, "extract_text"):
            # ExcelProcessor provides extract_text for unstructured regions
            text_content = await processor.extract_text(file_path, region)
        elif region.raw_text:
            text_content = region.raw_text

        if not text_content or not text_content.strip():
            return 0

        # Run through existing pipeline: chunk → embed → store
        chunks: list[ChunkResult] = self._text_chunker.chunk(text_content)
        if not chunks:
            return 0

        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = await self._embedding_generator.generate(chunk_texts)

        # Persist document and chunks to RAG_DB
        # Use a project_id placeholder if None (store without project scope)
        effective_project_id = project_id or uploaded_by  # Fallback for unscoped

        document = await self._store_results(
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            project_id=effective_project_id,
            uploaded_by=uploaded_by,
            chunks=chunks,
            embeddings=embeddings,
        )

        logger.debug(
            "Region indexed for RAG",
            extra={
                "file_name": file_name,
                "region_id": region.region_id,
                "chunk_count": len(chunks),
                "document_id": str(document.id),
            },
        )

        return len(chunks)

    async def _persist_region_only(
        self,
        file_id: UUID,
        region: DetectedRegion,
        classification: ClassificationResult,
    ) -> None:
        """Persist a DataRegion without creating a dataset (IGNORE/REVIEW_REQUIRED).

        Delegates to dataset_service which handles DataRegion creation
        for non-dataset strategies.
        """
        single_inspection = InspectionResult(
            file_name="",
            file_type="",
            regions=[region],
            metadata={},
        )
        await self._dataset_service.create_datasets_from_inspection(
            file_id=file_id,
            inspection=single_inspection,
            classifications=[classification],
        )

    # -------------------------------------------------------------------------
    # Shared storage helper
    # -------------------------------------------------------------------------

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
