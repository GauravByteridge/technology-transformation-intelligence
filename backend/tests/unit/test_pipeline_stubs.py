"""
Unit tests for document ingestion pipeline stub implementations.

Covers: extractors, chunker, embedder, and validator (task 10.2).
"""

import tempfile
from pathlib import Path

import pytest

from app.documents.chunker import FixedSizeChunker
from app.documents.embedder import DeterministicEmbeddingGenerator
from app.documents.extractors import (
    DocxContentExtractor,
    PdfContentExtractor,
    TxtContentExtractor,
)
from app.documents.validator import SimpleFileValidator
from app.errors.document_errors import (
    ContentExtractionError,
    DocumentValidationError,
)


# =============================================================================
# TxtContentExtractor Tests
# =============================================================================


class TestTxtContentExtractor:
    """Tests for TxtContentExtractor."""

    @pytest.fixture
    def extractor(self) -> TxtContentExtractor:
        return TxtContentExtractor()

    @pytest.mark.asyncio
    async def test_extracts_text_from_file(self, extractor: TxtContentExtractor, tmp_path: Path) -> None:
        file = tmp_path / "sample.txt"
        file.write_text("Hello, world!", encoding="utf-8")

        result = await extractor.extract(str(file), "txt")

        assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_extracts_multiline_content(self, extractor: TxtContentExtractor, tmp_path: Path) -> None:
        content = "Line 1\nLine 2\nLine 3"
        file = tmp_path / "multi.txt"
        file.write_text(content, encoding="utf-8")

        result = await extractor.extract(str(file), "txt")

        assert result == content

    @pytest.mark.asyncio
    async def test_raises_error_for_missing_file(self, extractor: TxtContentExtractor) -> None:
        with pytest.raises(ContentExtractionError):
            await extractor.extract("/nonexistent/path/file.txt", "txt")


# =============================================================================
# PdfContentExtractor Tests
# =============================================================================


class TestPdfContentExtractor:
    """Tests for PdfContentExtractor stub."""

    @pytest.mark.asyncio
    async def test_raises_not_implemented_error(self) -> None:
        extractor = PdfContentExtractor()
        with pytest.raises(NotImplementedError, match="Phase 1"):
            await extractor.extract("any/path.pdf", "pdf")


# =============================================================================
# DocxContentExtractor Tests
# =============================================================================


class TestDocxContentExtractor:
    """Tests for DocxContentExtractor stub."""

    @pytest.mark.asyncio
    async def test_raises_not_implemented_error(self) -> None:
        extractor = DocxContentExtractor()
        with pytest.raises(NotImplementedError, match="Phase 1"):
            await extractor.extract("any/path.docx", "docx")


# =============================================================================
# FixedSizeChunker Tests
# =============================================================================


class TestFixedSizeChunker:
    """Tests for FixedSizeChunker."""

    @pytest.fixture
    def chunker(self) -> FixedSizeChunker:
        return FixedSizeChunker()

    def test_returns_empty_list_for_empty_text(self, chunker: FixedSizeChunker) -> None:
        result = chunker.chunk("")
        assert result == []

    def test_single_chunk_for_short_text(self, chunker: FixedSizeChunker) -> None:
        result = chunker.chunk("short", chunk_size=100, overlap=0)
        assert len(result) == 1
        assert result[0].text == "short"
        assert result[0].chunk_index == 0

    def test_splits_into_multiple_chunks(self, chunker: FixedSizeChunker) -> None:
        text = "A" * 20
        result = chunker.chunk(text, chunk_size=10, overlap=0)
        assert len(result) == 2
        assert result[0].text == "A" * 10
        assert result[1].text == "A" * 10
        assert result[0].chunk_index == 0
        assert result[1].chunk_index == 1

    def test_overlap_produces_overlapping_content(self, chunker: FixedSizeChunker) -> None:
        text = "ABCDEFGHIJ"  # 10 chars
        result = chunker.chunk(text, chunk_size=6, overlap=2)
        # step = 6 - 2 = 4
        assert result[0].text == "ABCDEF"
        assert result[1].text == "EFGHIJ"

    def test_chunk_index_is_sequential(self, chunker: FixedSizeChunker) -> None:
        text = "X" * 50
        result = chunker.chunk(text, chunk_size=10, overlap=0)
        for i, chunk in enumerate(result):
            assert chunk.chunk_index == i

    def test_page_number_defaults_to_one_and_section_is_none(self, chunker: FixedSizeChunker) -> None:
        """Text without page breaks or headings: page_number=1, section=None."""
        result = chunker.chunk("some text", chunk_size=100, overlap=0)
        assert result[0].page_number == 1
        assert result[0].section is None


# =============================================================================
# DeterministicEmbeddingGenerator Tests
# =============================================================================


class TestDeterministicEmbeddingGenerator:
    """Tests for DeterministicEmbeddingGenerator."""

    @pytest.fixture
    def generator(self) -> DeterministicEmbeddingGenerator:
        return DeterministicEmbeddingGenerator(embedding_dimension=1536)

    @pytest.mark.asyncio
    async def test_produces_vector_of_correct_dimension(self, generator: DeterministicEmbeddingGenerator) -> None:
        result = await generator.generate(["hello world"])
        assert len(result) == 1
        assert len(result[0]) == 1536

    @pytest.mark.asyncio
    async def test_deterministic_same_input_same_output(self, generator: DeterministicEmbeddingGenerator) -> None:
        result_a = await generator.generate(["test input"])
        result_b = await generator.generate(["test input"])
        assert result_a == result_b

    @pytest.mark.asyncio
    async def test_different_inputs_produce_different_vectors(self, generator: DeterministicEmbeddingGenerator) -> None:
        result = await generator.generate(["hello", "world"])
        assert result[0] != result[1]

    @pytest.mark.asyncio
    async def test_multiple_texts_returns_one_vector_each(self, generator: DeterministicEmbeddingGenerator) -> None:
        texts = ["first", "second", "third"]
        result = await generator.generate(texts)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_values_in_zero_one_range(self, generator: DeterministicEmbeddingGenerator) -> None:
        result = await generator.generate(["range check"])
        for value in result[0]:
            assert 0.0 <= value < 1.0

    @pytest.mark.asyncio
    async def test_custom_dimension(self) -> None:
        gen = DeterministicEmbeddingGenerator(embedding_dimension=768)
        result = await gen.generate(["custom dim"])
        assert len(result[0]) == 768


# =============================================================================
# SimpleFileValidator Tests
# =============================================================================


class TestSimpleFileValidator:
    """Tests for SimpleFileValidator."""

    @pytest.fixture
    def validator(self) -> SimpleFileValidator:
        return SimpleFileValidator()

    @pytest.mark.asyncio
    async def test_accepts_valid_txt_file(self, validator: SimpleFileValidator) -> None:
        result = await validator.validate("report.txt", "txt", 1024)
        assert result is True

    @pytest.mark.asyncio
    async def test_accepts_valid_pdf_file(self, validator: SimpleFileValidator) -> None:
        result = await validator.validate("doc.pdf", "pdf", 5000)
        assert result is True

    @pytest.mark.asyncio
    async def test_accepts_valid_docx_file(self, validator: SimpleFileValidator) -> None:
        result = await validator.validate("doc.docx", "docx", 5000)
        assert result is True

    @pytest.mark.asyncio
    async def test_rejects_unsupported_file_type(self, validator: SimpleFileValidator) -> None:
        with pytest.raises(DocumentValidationError, match="Unsupported file type"):
            await validator.validate("image.png", "png", 1024)

    @pytest.mark.asyncio
    async def test_rejects_zero_size_file(self, validator: SimpleFileValidator) -> None:
        with pytest.raises(DocumentValidationError, match="greater than zero"):
            await validator.validate("empty.txt", "txt", 0)

    @pytest.mark.asyncio
    async def test_rejects_oversized_file(self, validator: SimpleFileValidator) -> None:
        large_size = 100 * 1024 * 1024  # 100 MB
        with pytest.raises(DocumentValidationError, match="exceeds maximum"):
            await validator.validate("big.txt", "txt", large_size)

    @pytest.mark.asyncio
    async def test_custom_allowed_types(self) -> None:
        validator = SimpleFileValidator(allowed_types={"png", "jpeg"})
        result = await validator.validate("photo.png", "png", 1024)
        assert result is True
