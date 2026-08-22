"""Tests for the IngestionOrchestrator — document pipeline glue logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.documents.orchestrator import IngestionOrchestrator
from app.documents.pipeline import ChunkResult, DocumentResult
from app.errors.document_errors import (
    ContentExtractionError,
    DocumentStorageError,
    DocumentValidationError,
)
from app.models.document import Document, DocumentChunk, Embedding


# ---------------------------------------------------------------------------
# Fake stage implementations satisfying the pipeline protocols
# ---------------------------------------------------------------------------


class FakeFileValidator:
    """Validates any file — always passes."""

    async def validate(self, file_name: str, file_type: str, file_size: int) -> bool:
        return True


class FakeContentExtractor:
    """Returns deterministic text content."""

    async def extract(self, file_path: str, file_type: str) -> str:
        return "This is the extracted text content from the document."


class FakeMetadataExtractor:
    """Returns fixed metadata."""

    async def extract_metadata(self, file_path: str, content: str) -> dict[str, str]:
        return {"title": "Test Document", "author": "Test Author"}


class FakeTextChunker:
    """Splits text into two fixed chunks."""

    def chunk(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list[ChunkResult]:
        return [
            ChunkResult(text="chunk one", chunk_index=0, page_number=1, section="intro"),
            ChunkResult(text="chunk two", chunk_index=1, page_number=1, section="body"),
        ]


class FakeEmbeddingGenerator:
    """Generates deterministic embeddings."""

    async def generate(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FailingFileValidator:
    """Always rejects validation."""

    async def validate(self, file_name: str, file_type: str, file_size: int) -> bool:
        raise DocumentValidationError(
            file_name=file_name,
            message=f"File '{file_name}' exceeds maximum size",
        )


class FailingContentExtractor:
    """Always fails extraction."""

    async def extract(self, file_path: str, file_type: str) -> str:
        raise ContentExtractionError(
            file_name=file_path,
            message="Failed to extract content",
        )


# ---------------------------------------------------------------------------
# Fake DocumentRepository
# ---------------------------------------------------------------------------


class FakeDocumentRepository:
    """In-memory document repository for testing."""

    def __init__(self) -> None:
        self.documents: list[Document] = []
        self.chunks: list[DocumentChunk] = []
        self.embeddings: list[Embedding] = []

    async def create_document(self, document: Document) -> Document:
        document.id = str(uuid4())
        self.documents.append(document)
        return document

    async def create_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        chunk.id = str(uuid4())
        self.chunks.append(chunk)
        return chunk

    async def create_embedding(self, embedding: Embedding) -> Embedding:
        embedding.id = str(uuid4())
        self.embeddings.append(embedding)
        return embedding


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIngestionOrchestrator:
    """Verify the orchestrator chains stages and stores results."""

    @pytest.fixture
    def repository(self) -> FakeDocumentRepository:
        return FakeDocumentRepository()

    @pytest.fixture
    def orchestrator(self, repository: FakeDocumentRepository) -> IngestionOrchestrator:
        return IngestionOrchestrator(
            file_validator=FakeFileValidator(),
            content_extractor=FakeContentExtractor(),
            metadata_extractor=FakeMetadataExtractor(),
            text_chunker=FakeTextChunker(),
            embedding_generator=FakeEmbeddingGenerator(),
            document_repository=repository,
        )

    @pytest.mark.asyncio
    async def test_successful_ingestion_returns_document_result(
        self, orchestrator: IngestionOrchestrator
    ) -> None:
        result = await orchestrator.ingest(
            file_path="/tmp/test.txt",
            file_name="test.txt",
            file_type="text/plain",
            file_size=1024,
            project_id=uuid4(),
            uploaded_by=uuid4(),
        )

        assert isinstance(result, DocumentResult)
        assert result.chunk_count == 2
        assert result.status == "completed"
        assert result.document_id is not None

    @pytest.mark.asyncio
    async def test_stores_document_record(
        self, orchestrator: IngestionOrchestrator, repository: FakeDocumentRepository
    ) -> None:
        project_id = uuid4()
        uploaded_by = uuid4()

        await orchestrator.ingest(
            file_path="/tmp/report.txt",
            file_name="report.txt",
            file_type="text/plain",
            file_size=2048,
            project_id=project_id,
            uploaded_by=uploaded_by,
        )

        assert len(repository.documents) == 1
        doc = repository.documents[0]
        assert doc.file_name == "report.txt"
        assert doc.file_type == "text/plain"
        assert doc.file_size == 2048
        assert doc.project_id == str(project_id)
        assert doc.uploaded_by == str(uploaded_by)
        assert doc.processing_status == "completed"

    @pytest.mark.asyncio
    async def test_stores_chunks_with_positional_info(
        self, orchestrator: IngestionOrchestrator, repository: FakeDocumentRepository
    ) -> None:
        await orchestrator.ingest(
            file_path="/tmp/doc.txt",
            file_name="doc.txt",
            file_type="text/plain",
            file_size=512,
            project_id=uuid4(),
            uploaded_by=uuid4(),
        )

        assert len(repository.chunks) == 2
        assert repository.chunks[0].chunk_index == 0
        assert repository.chunks[0].content == "chunk one"
        assert repository.chunks[0].page_number == 1
        assert repository.chunks[0].section == "intro"
        assert repository.chunks[1].chunk_index == 1
        assert repository.chunks[1].section == "body"

    @pytest.mark.asyncio
    async def test_stores_embeddings_for_each_chunk(
        self, orchestrator: IngestionOrchestrator, repository: FakeDocumentRepository
    ) -> None:
        await orchestrator.ingest(
            file_path="/tmp/doc.txt",
            file_name="doc.txt",
            file_type="text/plain",
            file_size=512,
            project_id=uuid4(),
            uploaded_by=uuid4(),
        )

        assert len(repository.embeddings) == 2
        assert repository.embeddings[0].dimension == 3
        assert repository.embeddings[0].model_name == "deterministic-stub"

    @pytest.mark.asyncio
    async def test_validation_failure_propagates_error(
        self, repository: FakeDocumentRepository
    ) -> None:
        orchestrator = IngestionOrchestrator(
            file_validator=FailingFileValidator(),
            content_extractor=FakeContentExtractor(),
            metadata_extractor=FakeMetadataExtractor(),
            text_chunker=FakeTextChunker(),
            embedding_generator=FakeEmbeddingGenerator(),
            document_repository=repository,
        )

        with pytest.raises(DocumentValidationError) as exc_info:
            await orchestrator.ingest(
                file_path="/tmp/huge.pdf",
                file_name="huge.pdf",
                file_type="application/pdf",
                file_size=999_999_999,
                project_id=uuid4(),
                uploaded_by=uuid4(),
            )

        assert exc_info.value.file_name == "huge.pdf"
        assert len(repository.documents) == 0

    @pytest.mark.asyncio
    async def test_extraction_failure_propagates_error(
        self, repository: FakeDocumentRepository
    ) -> None:
        orchestrator = IngestionOrchestrator(
            file_validator=FakeFileValidator(),
            content_extractor=FailingContentExtractor(),
            metadata_extractor=FakeMetadataExtractor(),
            text_chunker=FakeTextChunker(),
            embedding_generator=FakeEmbeddingGenerator(),
            document_repository=repository,
        )

        with pytest.raises(ContentExtractionError):
            await orchestrator.ingest(
                file_path="/tmp/corrupt.pdf",
                file_name="corrupt.pdf",
                file_type="application/pdf",
                file_size=1024,
                project_id=uuid4(),
                uploaded_by=uuid4(),
            )

        assert len(repository.documents) == 0

    @pytest.mark.asyncio
    async def test_storage_failure_raises_document_storage_error(
        self,
    ) -> None:
        """If repository throws, orchestrator wraps it as DocumentStorageError."""

        class FailingRepository:
            async def create_document(self, document: Document) -> Document:
                raise RuntimeError("DB connection lost")

            async def create_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
                raise RuntimeError("DB connection lost")

            async def create_embedding(self, embedding: Embedding) -> Embedding:
                raise RuntimeError("DB connection lost")

        orchestrator = IngestionOrchestrator(
            file_validator=FakeFileValidator(),
            content_extractor=FakeContentExtractor(),
            metadata_extractor=FakeMetadataExtractor(),
            text_chunker=FakeTextChunker(),
            embedding_generator=FakeEmbeddingGenerator(),
            document_repository=FailingRepository(),  # type: ignore[arg-type]
        )

        with pytest.raises(DocumentStorageError) as exc_info:
            await orchestrator.ingest(
                file_path="/tmp/test.txt",
                file_name="test.txt",
                file_type="text/plain",
                file_size=512,
                project_id=uuid4(),
                uploaded_by=uuid4(),
            )

        assert exc_info.value.file_name == "test.txt"
        assert "DB connection lost" in (exc_info.value.detail or "")
