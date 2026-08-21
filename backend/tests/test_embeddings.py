"""Unit tests for the EmbeddingGenerator service.

Tests cover:
- Successful embedding generation for single and multiple texts
- Batch processing returns correct number of embeddings
- Each embedding has consistent dimensionality
- Empty list input raises ValueError
- Different texts produce different embeddings
- Embeddings are plain lists of floats
"""

import pytest
from services.embeddings import EmbeddingGenerator


@pytest.fixture
def generator():
    """Create an EmbeddingGenerator instance for testing."""
    return EmbeddingGenerator()


class TestEmbeddingGeneratorInit:
    """Test EmbeddingGenerator initialization."""

    def test_creates_instance(self):
        gen = EmbeddingGenerator()
        assert gen._embedding_fn is not None


class TestEmbeddingGeneratorGenerate:
    """Test the generate() method."""

    def test_single_text_returns_one_embedding(self, generator):
        result = generator.generate(["Hello world"])
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert all(isinstance(v, float) for v in result[0])

    def test_multiple_texts_returns_matching_count(self, generator):
        texts = ["First chunk", "Second chunk", "Third chunk"]
        result = generator.generate(texts)
        assert len(result) == 3

    def test_embeddings_have_consistent_dimensions(self, generator):
        texts = ["Short text", "A longer text with more words in it"]
        result = generator.generate(texts)
        assert len(result[0]) == len(result[1])
        # ChromaDB's default model produces 384-dimensional embeddings
        assert len(result[0]) == 384

    def test_empty_list_raises_value_error(self, generator):
        with pytest.raises(ValueError, match="Cannot generate embeddings for an empty list"):
            generator.generate([])

    def test_different_texts_produce_different_embeddings(self, generator):
        texts = ["The cat sat on the mat", "Quantum physics explains the universe"]
        result = generator.generate(texts)
        # Embeddings for semantically different texts should differ
        assert result[0] != result[1]

    def test_batch_processing_efficiency(self, generator):
        """Verify batch of 10 texts processes successfully."""
        texts = [f"Document chunk number {i} with some content" for i in range(10)]
        result = generator.generate(texts)
        assert len(result) == 10
        assert all(len(emb) == 384 for emb in result)

    def test_embeddings_are_plain_lists(self, generator):
        """Ensure embeddings are plain Python lists, not numpy arrays."""
        result = generator.generate(["Test text"])
        assert type(result[0]) is list
        assert type(result[0][0]) is float
