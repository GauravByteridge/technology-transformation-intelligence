"""
Unit tests for the chat API endpoint.

Tests POST /api/chat with mocked RAG pipeline to avoid external
API dependencies (Groq, ChromaDB).
"""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from models.schemas import ChatResponse


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/chat tests
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    """Tests for POST /api/chat endpoint."""

    @patch("api.chat.RAGPipeline")
    def test_chat_success(self, mock_pipeline_class, client):
        """A valid question returns an answer with sources."""
        mock_pipeline = MagicMock()
        mock_pipeline.query.return_value = ChatResponse(
            answer="The project budget is $1.5M.",
            sources=["budget_report.pdf", "costs.xlsx"],
        )
        mock_pipeline_class.return_value = mock_pipeline

        response = client.post("/api/chat", json={"question": "What is the project budget?"})

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "The project budget is $1.5M."
        assert data["sources"] == ["budget_report.pdf", "costs.xlsx"]
        mock_pipeline.query.assert_called_once_with(question="What is the project budget?")

    @patch("api.chat.RAGPipeline")
    def test_chat_no_relevant_chunks(self, mock_pipeline_class, client):
        """When no relevant chunks are found, pipeline returns helpful message."""
        mock_pipeline = MagicMock()
        mock_pipeline.query.return_value = ChatResponse(
            answer="No relevant information was found in the project data. "
                   "Please upload files related to your question.",
            sources=[],
        )
        mock_pipeline_class.return_value = mock_pipeline

        response = client.post("/api/chat", json={"question": "What about quantum physics?"})

        assert response.status_code == 200
        data = response.json()
        assert "No relevant information" in data["answer"]
        assert data["sources"] == []

    @patch("api.chat.RAGPipeline")
    def test_chat_groq_api_failure_returns_503(self, mock_pipeline_class, client):
        """When Groq API fails (RuntimeError), returns 503."""
        mock_pipeline = MagicMock()
        mock_pipeline.query.side_effect = RuntimeError("AI service returned an error")
        mock_pipeline_class.return_value = mock_pipeline

        response = client.post("/api/chat", json={"question": "What is the status?"})

        assert response.status_code == 503
        data = response.json()
        assert "AI service is unavailable" in data["detail"]

    def test_chat_empty_question_returns_400(self, client):
        """Empty question returns 400 error."""
        response = client.post("/api/chat", json={"question": ""})

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "empty" in data["detail"].lower()

    def test_chat_whitespace_question_returns_400(self, client):
        """Whitespace-only question returns 400 error."""
        response = client.post("/api/chat", json={"question": "   "})

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "empty" in data["detail"].lower()

    @patch("api.chat.RAGPipeline")
    def test_chat_strips_question_whitespace(self, mock_pipeline_class, client):
        """Question is trimmed before being passed to the pipeline."""
        mock_pipeline = MagicMock()
        mock_pipeline.query.return_value = ChatResponse(
            answer="Answer here.",
            sources=["file.pdf"],
        )
        mock_pipeline_class.return_value = mock_pipeline

        response = client.post("/api/chat", json={"question": "  What is the budget?  "})

        assert response.status_code == 200
        mock_pipeline.query.assert_called_once_with(question="What is the budget?")

    def test_chat_missing_question_field_returns_422(self, client):
        """Missing question field returns 422 validation error."""
        response = client.post("/api/chat", json={})

        assert response.status_code == 422
