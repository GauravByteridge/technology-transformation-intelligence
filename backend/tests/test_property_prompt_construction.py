"""
Property-based test for Prompt Construction Completeness (Property 7).

**Validates: Requirements 6.4**

For any user question and any set of retrieved context chunks, the constructed
RAG prompt SHALL contain:
- The complete user question text
- All retrieved chunk content
- Clear separation between context and question
"""

import sys
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Mock out db.database to avoid PostgreSQL import dependency in tests
sys.modules.setdefault("db.database", MagicMock())

from unittest.mock import patch

from services.rag_pipeline import RAGPipeline


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for non-empty question strings (printable ASCII, no control chars)
questions = st.text(
    alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E),
    min_size=1,
    max_size=500,
)

# Strategy for a single non-empty chunk
chunk_text = st.text(
    alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E),
    min_size=1,
    max_size=1000,
)

# Strategy for a list of context chunks (0 to 10 chunks)
chunk_lists = st.lists(chunk_text, min_size=0, max_size=10)

# Strategy for non-empty chunk lists (at least 1 chunk)
non_empty_chunk_lists = st.lists(chunk_text, min_size=1, max_size=10)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pipeline() -> RAGPipeline:
    """Create a RAGPipeline instance with mocked dependencies."""
    with patch("services.rag_pipeline.EmbeddingGenerator"):
        return RAGPipeline(groq_api_key="test-key")


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestPromptConstructionCompleteness:
    """
    Property 7: Prompt Construction Completeness

    **Validates: Requirements 6.4**

    For any user question and any set of retrieved context chunks, the
    constructed RAG prompt SHALL contain:
    - The complete user question text
    - All retrieved chunk content
    - Clear separation between context and question
    """

    @given(question=questions, chunks=chunk_lists)
    @settings(max_examples=200)
    def test_prompt_contains_complete_question(self, question, chunks):
        """
        Property: For any user question and any chunk list, the built prompt
        contains the complete user question text verbatim.
        """
        assume(question.strip())

        pipeline = _make_pipeline()
        prompt = pipeline.build_prompt(question, chunks)

        assert question in prompt, (
            f"User question not found in prompt. "
            f"Question: {repr(question[:100])}"
        )

    @given(question=questions, chunks=non_empty_chunk_lists)
    @settings(max_examples=200)
    def test_prompt_contains_all_chunk_content(self, question, chunks):
        """
        Property: For any user question and any non-empty set of context
        chunks, the built prompt contains every chunk's content verbatim.
        """
        assume(question.strip())

        pipeline = _make_pipeline()
        prompt = pipeline.build_prompt(question, chunks)

        for i, chunk in enumerate(chunks):
            assert chunk in prompt, (
                f"Chunk {i} not found in prompt. "
                f"Chunk content: {repr(chunk[:100])}"
            )

    @given(question=questions, chunks=chunk_lists)
    @settings(max_examples=200)
    def test_prompt_has_clear_separation(self, question, chunks):
        """
        Property: For any user question and any chunk list, the built prompt
        has clear separation markers between context and question sections,
        with context appearing before the question.
        """
        assume(question.strip())

        pipeline = _make_pipeline()
        prompt = pipeline.build_prompt(question, chunks)

        # Must contain context and question section markers
        assert "=== CONTEXT ===" in prompt, "Missing context section marker"
        assert "=== QUESTION ===" in prompt, "Missing question section marker"

        # Context section must appear before question section
        context_pos = prompt.find("=== CONTEXT ===")
        question_pos = prompt.find("=== QUESTION ===")
        assert context_pos < question_pos, (
            f"Context section (pos {context_pos}) must appear before "
            f"question section (pos {question_pos})"
        )
