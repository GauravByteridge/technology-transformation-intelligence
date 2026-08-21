"""Unit tests for the Chunker service.

Tests cover:
- Empty and whitespace-only input
- Text shorter than chunk_size
- Text exactly at chunk_size boundary
- Text requiring multiple chunks
- Overlap between adjacent chunks
- Content preservation (no data loss)
"""

import pytest
from services.chunker import Chunker


class TestChunkerInit:
    """Test Chunker initialization and parameter validation."""

    def test_default_parameters(self):
        chunker = Chunker()
        assert chunker.chunk_size == 900
        assert chunker.overlap == 100

    def test_custom_parameters(self):
        chunker = Chunker(chunk_size=850, overlap=50)
        assert chunker.chunk_size == 850
        assert chunker.overlap == 50

    def test_chunk_size_below_800_raises(self):
        with pytest.raises(ValueError, match="chunk_size must be between 800 and 1000"):
            Chunker(chunk_size=799)

    def test_chunk_size_above_1000_raises(self):
        with pytest.raises(ValueError, match="chunk_size must be between 800 and 1000"):
            Chunker(chunk_size=1001)

    def test_negative_overlap_raises(self):
        with pytest.raises(ValueError, match="overlap must be non-negative"):
            Chunker(overlap=-1)

    def test_overlap_equal_to_chunk_size_raises(self):
        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            Chunker(chunk_size=900, overlap=900)

    def test_overlap_greater_than_chunk_size_raises(self):
        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            Chunker(chunk_size=900, overlap=950)


class TestChunkerEdgeCases:
    """Test edge cases: empty text, short text, boundary conditions."""

    def test_empty_string_returns_empty_list(self):
        chunker = Chunker()
        assert chunker.chunk("") == []

    def test_whitespace_only_returns_empty_list(self):
        chunker = Chunker()
        assert chunker.chunk("   \n\t  ") == []

    def test_text_shorter_than_chunk_size(self):
        chunker = Chunker(chunk_size=900)
        text = "Short text content."
        result = chunker.chunk(text)
        assert result == [text]

    def test_text_exactly_chunk_size(self):
        chunker = Chunker(chunk_size=900)
        text = "a" * 900
        result = chunker.chunk(text)
        assert result == [text]

    def test_single_character(self):
        chunker = Chunker()
        result = chunker.chunk("x")
        assert result == ["x"]


class TestChunkerChunking:
    """Test core chunking logic with multiple chunks."""

    def test_two_chunks_with_overlap(self):
        chunker = Chunker(chunk_size=900, overlap=100)
        # Text of length 1600 should produce 2 chunks
        # Step = 900 - 100 = 800
        # Chunk 1: [0:900], Chunk 2: [800:1600]
        text = "a" * 800 + "b" * 800  # 1600 chars
        result = chunker.chunk(text)

        assert len(result) == 2
        assert len(result[0]) == 900
        assert len(result[1]) == 800  # Last chunk can be shorter
        # Check overlap: last 100 chars of chunk 1 == first 100 chars of chunk 2
        assert result[0][-100:] == result[1][:100]

    def test_multiple_chunks_correct_count(self):
        chunker = Chunker(chunk_size=900, overlap=100)
        step = 900 - 100  # 800
        # Text of 2500 chars: chunks starting at 0, 800, 1600
        # Chunk 1: [0:900], Chunk 2: [800:1700], Chunk 3: [1600:2500]
        text = "x" * 2500
        result = chunker.chunk(text)

        assert len(result) == 3
        assert len(result[0]) == 900
        assert len(result[1]) == 900
        assert len(result[2]) == 900  # 2500-1600=900

    def test_overlap_content_matches(self):
        chunker = Chunker(chunk_size=900, overlap=100)
        # Create recognizable text
        text = "".join([str(i % 10) for i in range(2000)])
        result = chunker.chunk(text)

        # Verify overlap between all adjacent chunks
        for i in range(len(result) - 1):
            overlap_from_current = result[i][-chunker.overlap:]
            overlap_from_next = result[i + 1][:chunker.overlap]
            assert overlap_from_current == overlap_from_next, (
                f"Overlap mismatch between chunk {i} and {i+1}"
            )

    def test_no_content_loss(self):
        """Verify that reconstructing from chunks recovers the original text."""
        chunker = Chunker(chunk_size=900, overlap=100)
        text = "".join([chr(65 + (i % 26)) for i in range(3000)])
        result = chunker.chunk(text)

        # Reconstruct: take full first chunk, then non-overlapping part of subsequent chunks
        reconstructed = result[0]
        for chunk in result[1:]:
            # Skip the overlap portion (first `overlap` chars are repeated)
            reconstructed += chunk[chunker.overlap:]

        assert reconstructed == text

    def test_last_chunk_can_be_shorter(self):
        chunker = Chunker(chunk_size=900, overlap=100)
        step = 800
        # 901 chars: chunk 1 = [0:900], chunk 2 = [800:901] (101 chars)
        text = "z" * 901
        result = chunker.chunk(text)

        assert len(result) == 2
        assert len(result[0]) == 900
        assert len(result[1]) == 101  # Remaining after step

    def test_chunk_size_boundary_values(self):
        """All chunks except last should be exactly chunk_size."""
        chunker = Chunker(chunk_size=800, overlap=100)
        text = "m" * 5000
        result = chunker.chunk(text)

        for chunk in result[:-1]:
            assert len(chunk) == 800
        # Last chunk can be any size > 0
        assert 0 < len(result[-1]) <= 800
