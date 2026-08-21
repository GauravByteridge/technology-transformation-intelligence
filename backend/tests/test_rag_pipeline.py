"""Unit tests for RAGPipeline service."""

import sys
import pytest
from unittest.mock import patch, MagicMock

# Mock out db.database to avoid PostgreSQL import dependency in tests
sys.modules.setdefault("db.database", MagicMock())

from services.rag_pipeline import RAGPipeline
from models.schemas import ChatResponse


class TestBuildPrompt:
    """Tests for the prompt construction method."""

    def setup_method(self):
        """Create a RAGPipeline instance with dummy config."""
        with patch("services.rag_pipeline.EmbeddingGenerator"):
            self.pipeline = RAGPipeline(groq_api_key="test-key")

    def test_prompt_contains_question(self):
        """The prompt must contain the complete user question."""
        question = "What is the project budget?"
        chunks = ["Budget is $1M for Q1."]
        prompt = self.pipeline.build_prompt(question, chunks)
        assert question in prompt

    def test_prompt_contains_all_chunks(self):
        """The prompt must contain all retrieved context chunks."""
        question = "Summary?"
        chunks = ["Chunk one content.", "Chunk two content.", "Chunk three content."]
        prompt = self.pipeline.build_prompt(question, chunks)
        for chunk in chunks:
            assert chunk in prompt

    def test_prompt_has_clear_separation(self):
        """The prompt must have clear separation between context and question."""
        question = "What happened in Q2?"
        chunks = ["Q2 revenue grew 10%."]
        prompt = self.pipeline.build_prompt(question, chunks)
        # Context section should appear before question section
        context_pos = prompt.find("=== CONTEXT ===")
        question_pos = prompt.find("=== QUESTION ===")
        assert context_pos < question_pos
        assert context_pos >= 0
        assert question_pos >= 0

    def test_prompt_with_empty_chunks_list(self):
        """The prompt should still be valid even with an empty chunks list."""
        question = "Any data?"
        chunks = []
        prompt = self.pipeline.build_prompt(question, chunks)
        assert question in prompt
        assert "=== CONTEXT ===" in prompt


class TestExtractContextAndSources:
    """Tests for extraction of context text and source files from search results."""

    def setup_method(self):
        with patch("services.rag_pipeline.EmbeddingGenerator"):
            self.pipeline = RAGPipeline(groq_api_key="test-key")

    def test_extracts_documents_and_sources(self):
        """Should extract document texts and unique source file names."""
        results = {
            "documents": [["text chunk 1", "text chunk 2"]],
            "metadatas": [[
                {"file_name": "report.pdf", "file_id": 1},
                {"file_name": "data.csv", "file_id": 2},
            ]],
            "distances": [[0.1, 0.2]],
        }
        chunks, sources = self.pipeline._extract_context_and_sources(results)
        assert chunks == ["text chunk 1", "text chunk 2"]
        assert sources == {"report.pdf", "data.csv"}

    def test_deduplicates_source_files(self):
        """Should deduplicate source file names."""
        results = {
            "documents": [["chunk a", "chunk b"]],
            "metadatas": [[
                {"file_name": "report.pdf", "file_id": 1},
                {"file_name": "report.pdf", "file_id": 1},
            ]],
            "distances": [[0.1, 0.15]],
        }
        chunks, sources = self.pipeline._extract_context_and_sources(results)
        assert len(sources) == 1
        assert "report.pdf" in sources

    def test_handles_empty_results(self):
        """Should handle empty search results gracefully."""
        results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        chunks, sources = self.pipeline._extract_context_and_sources(results)
        assert chunks == []
        assert sources == set()

    def test_handles_missing_keys(self):
        """Should handle missing keys in results dict."""
        results = {}
        chunks, sources = self.pipeline._extract_context_and_sources(results)
        assert chunks == []
        assert sources == set()


class TestQueryFlow:
    """Tests for the full query method with mocked dependencies."""

    @patch("services.rag_pipeline.query_embeddings")
    @patch("services.rag_pipeline.EmbeddingGenerator")
    def test_returns_no_info_message_when_no_chunks(self, mock_emb_cls, mock_query):
        """Should return a helpful message when no relevant chunks are found."""
        mock_emb = MagicMock()
        mock_emb.generate.return_value = [[0.1] * 384]
        mock_emb_cls.return_value = mock_emb

        mock_query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        pipeline = RAGPipeline(groq_api_key="test-key")
        result = pipeline.query("What is the budget?")

        assert isinstance(result, ChatResponse)
        assert "No relevant information" in result.answer
        assert result.sources == []

    @patch("services.rag_pipeline.query_embeddings")
    @patch("services.rag_pipeline.EmbeddingGenerator")
    def test_raises_on_missing_api_key(self, mock_emb_cls, mock_query):
        """Should raise RuntimeError if Groq API key is not set."""
        mock_emb = MagicMock()
        mock_emb.generate.return_value = [[0.1] * 384]
        mock_emb_cls.return_value = mock_emb

        mock_query.return_value = {
            "documents": [["Some context text here"]],
            "metadatas": [[{"file_name": "report.pdf", "file_id": 1}]],
            "distances": [[0.1]],
        }

        pipeline = RAGPipeline(groq_api_key="")
        with pytest.raises(RuntimeError, match="Groq API key is not configured"):
            pipeline.query("What happened?")

    @patch("services.rag_pipeline.httpx.Client")
    @patch("services.rag_pipeline.query_embeddings")
    @patch("services.rag_pipeline.EmbeddingGenerator")
    def test_successful_query_returns_chat_response(
        self, mock_emb_cls, mock_query, mock_httpx_client
    ):
        """Should return ChatResponse with answer and sources on success."""
        mock_emb = MagicMock()
        mock_emb.generate.return_value = [[0.1] * 384]
        mock_emb_cls.return_value = mock_emb

        mock_query.return_value = {
            "documents": [["Budget is $1M for Q1."]],
            "metadatas": [[{"file_name": "budget.xlsx", "file_id": 1}]],
            "distances": [[0.05]],
        }

        # Mock the httpx client context manager
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "The budget is $1M for Q1."}}
            ]
        }
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value = mock_client_instance

        pipeline = RAGPipeline(groq_api_key="test-key")
        result = pipeline.query("What is the budget?")

        assert isinstance(result, ChatResponse)
        assert "budget" in result.answer.lower()
        assert "budget.xlsx" in result.sources
