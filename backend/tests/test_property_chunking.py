"""
Property-based test for Chunking Produces Valid Segments (Property 6).

**Validates: Requirements 4.3**

For any input text with length greater than 0, the Chunker SHALL produce chunks where:
- Each chunk (except possibly the last) has length between 800 and 1000 characters
- Adjacent chunks have appropriate character overlap
- The concatenation of unique content from all chunks reconstructs the original text
  (no content loss)
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from services.chunker import Chunker


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for valid chunk_size values (800-1000)
chunk_sizes = st.integers(min_value=800, max_value=1000)

# Strategy for overlap values (will be constrained relative to chunk_size)
overlaps = st.integers(min_value=1, max_value=400)

# Strategy for non-empty text of various lengths (always has content)
non_empty_text = st.text(
    alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E),
    min_size=1,
    max_size=10000,
)

# Strategy for longer text that forces multiple chunks
long_text = st.text(
    alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E),
    min_size=1001,
    max_size=10000,
)

# Strategy for text that includes whitespace but is not all whitespace
text_with_whitespace = st.builds(
    lambda prefix, body, suffix: prefix + body + suffix,
    prefix=st.text(alphabet=" \t\n", min_size=0, max_size=10),
    body=st.text(
        alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
        min_size=1,
        max_size=5000,
    ),
    suffix=st.text(alphabet=" \t\n", min_size=0, max_size=10),
)


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestChunkingProperty:
    """
    Property 6: Chunking Produces Valid Segments

    **Validates: Requirements 4.3**

    For any input text with length greater than 0, the Chunker SHALL produce
    chunks where:
    - Each chunk (except possibly the last) has length between 800 and 1000 chars
    - Adjacent chunks have appropriate character overlap
    - The concatenation of unique content from all chunks reconstructs the
      original text (no content loss)
    """

    @given(text=non_empty_text, chunk_size=chunk_sizes, overlap=overlaps)
    @settings(max_examples=200)
    def test_chunk_size_bounds(self, text, chunk_size, overlap):
        """
        Property: For any non-empty text and valid chunker configuration,
        all chunks except possibly the last have length exactly equal to
        chunk_size (which is between 800 and 1000).
        """
        assume(overlap < chunk_size)
        assume(text.strip())  # Ensure text is not whitespace-only

        chunker = Chunker(chunk_size=chunk_size, overlap=overlap)
        chunks = chunker.chunk(text)

        assert len(chunks) > 0, "Non-empty, non-whitespace text must produce at least one chunk"

        if len(chunks) > 1:
            # All chunks except the last must be exactly chunk_size
            for i, chunk in enumerate(chunks[:-1]):
                assert len(chunk) == chunk_size, (
                    f"Chunk {i} has length {len(chunk)}, expected {chunk_size}"
                )
            # Last chunk must be between 1 and chunk_size characters
            assert 1 <= len(chunks[-1]) <= chunk_size, (
                f"Last chunk has length {len(chunks[-1])}, "
                f"expected between 1 and {chunk_size}"
            )
        else:
            # Single chunk: length should be <= chunk_size
            assert 1 <= len(chunks[0]) <= chunk_size

    @given(text=long_text, chunk_size=chunk_sizes, overlap=overlaps)
    @settings(max_examples=200)
    def test_adjacent_chunks_have_overlap(self, text, chunk_size, overlap):
        """
        Property: For any text producing multiple chunks, adjacent chunks
        share exactly `overlap` characters at their boundaries.
        """
        assume(overlap < chunk_size)
        assume(text.strip())

        chunker = Chunker(chunk_size=chunk_size, overlap=overlap)
        chunks = chunker.chunk(text)

        assume(len(chunks) > 1)  # Need multiple chunks to test overlap

        for i in range(len(chunks) - 1):
            tail_of_current = chunks[i][-overlap:]
            head_of_next = chunks[i + 1][:overlap]
            assert tail_of_current == head_of_next, (
                f"Overlap mismatch between chunk {i} and {i+1}: "
                f"tail={repr(tail_of_current[:50])}, head={repr(head_of_next[:50])}"
            )

    @given(text=non_empty_text, chunk_size=chunk_sizes, overlap=overlaps)
    @settings(max_examples=200)
    def test_content_preservation(self, text, chunk_size, overlap):
        """
        Property: For any non-empty text, concatenating the unique content
        from all chunks (first chunk fully, then non-overlapping portion of
        subsequent chunks) reconstructs the original text exactly.
        """
        assume(overlap < chunk_size)
        assume(text.strip())

        chunker = Chunker(chunk_size=chunk_size, overlap=overlap)
        chunks = chunker.chunk(text)

        assert len(chunks) > 0

        # Reconstruct text from chunks
        if len(chunks) == 1:
            reconstructed = chunks[0]
        else:
            reconstructed = chunks[0]
            for chunk in chunks[1:]:
                # Skip the overlapping portion
                reconstructed += chunk[overlap:]

        assert reconstructed == text, (
            f"Content loss detected: original length={len(text)}, "
            f"reconstructed length={len(reconstructed)}"
        )

    @given(text=text_with_whitespace, chunk_size=chunk_sizes, overlap=overlaps)
    @settings(max_examples=100)
    def test_non_empty_chunks_produced(self, text, chunk_size, overlap):
        """
        Property: For any text that contains at least one non-whitespace
        character, the chunker produces at least one chunk with content.
        """
        assume(overlap < chunk_size)
        assume(text.strip())

        chunker = Chunker(chunk_size=chunk_size, overlap=overlap)
        chunks = chunker.chunk(text)

        assert len(chunks) >= 1, "Text with non-whitespace content must produce chunks"
        # Each chunk should have some content
        for i, chunk in enumerate(chunks):
            assert len(chunk) > 0, f"Chunk {i} is empty"
