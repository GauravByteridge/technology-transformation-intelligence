"""
Document ingestion pipeline stage protocols and result types.

Defines the contracts for each processing stage in the document
ingestion pipeline: validation, extraction, metadata, chunking,
embedding, and orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ChunkResult:
    """Result of splitting text into a single chunk.

    Attributes:
        text: The chunk text content.
        chunk_index: Zero-based position of this chunk in the sequence.
        page_number: Source page number if available (e.g., from PDF).
        section: Source section heading if available.
    """

    text: str
    chunk_index: int
    page_number: int | None = None
    section: str | None = None


@dataclass(frozen=True)
class DocumentResult:
    """Result of a successful document ingestion.

    Attributes:
        document_id: UUID assigned to the stored document.
        chunk_count: Total number of chunks produced and stored.
        status: Final pipeline status (e.g., "completed", "partial").
    """

    document_id: UUID
    chunk_count: int
    status: str


class FileValidator(Protocol):
    """Validates uploaded file metadata before processing begins."""

    async def validate(self, file_name: str, file_type: str, file_size: int) -> bool:
        """Check whether the file is acceptable for ingestion.

        Args:
            file_name: Original file name including extension.
            file_type: MIME type or extension identifier.
            file_size: File size in bytes.

        Returns:
            True if the file passes validation.

        Raises:
            DocumentValidationError: If the file fails validation checks.
        """
        ...


class ContentExtractor(Protocol):
    """Extracts raw text content from a document file."""

    async def extract(self, file_path: str, file_type: str) -> str:
        """Extract text from the file at the given path.

        Args:
            file_path: Absolute or relative path to the document.
            file_type: MIME type or extension identifier.

        Returns:
            Extracted text content as a single string.

        Raises:
            ContentExtractionError: If text extraction fails.
        """
        ...


class MetadataExtractor(Protocol):
    """Extracts metadata from a document and its content."""

    async def extract_metadata(self, file_path: str, content: str) -> dict[str, str]:
        """Extract key-value metadata from the document.

        Args:
            file_path: Path to the source file.
            content: Previously extracted text content.

        Returns:
            Dictionary of metadata key-value pairs.

        Raises:
            MetadataExtractionError: If metadata extraction fails.
        """
        ...


class TextChunker(Protocol):
    """Splits text content into overlapping chunks for embedding."""

    def chunk(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list[ChunkResult]:
        """Split text into chunks with configurable size and overlap.

        Args:
            text: Full text content to split.
            chunk_size: Target number of characters per chunk.
            overlap: Number of overlapping characters between consecutive chunks.

        Returns:
            Ordered list of ChunkResult instances.

        Raises:
            ChunkingError: If chunking logic encounters a failure.
        """
        ...


class EmbeddingGenerator(Protocol):
    """Generates vector embeddings for text chunks."""

    async def generate(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for the provided text segments.

        Args:
            texts: List of text segments to embed.

        Returns:
            List of embedding vectors, one per input text.

        Raises:
            EmbeddingGenerationError: If the embedding provider fails.
        """
        ...


class IngestionPipeline(Protocol):
    """Orchestrates the full document ingestion flow.

    Chains all pipeline stages together: validation → extraction →
    metadata → chunking → embedding → storage.
    """

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

        Args:
            file_path: Path to the uploaded file.
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
        ...
