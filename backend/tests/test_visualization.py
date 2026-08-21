"""Unit tests for the VisualizationGenerator service."""

import json
import sys
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

# Mock db.database before importing visualization (avoids psycopg2 dependency)
sys.modules.setdefault("psycopg2", MagicMock())
sys.modules.setdefault("psycopg2.extensions", MagicMock())

from services.visualization import VisualizationGenerator
from models.schemas import ChartConfig


class TestVisualizationGenerator:
    """Tests for VisualizationGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = VisualizationGenerator()

    def test_empty_query_raises_value_error(self):
        """Empty queries should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            self.generator.generate("")

    def test_whitespace_query_raises_value_error(self):
        """Whitespace-only queries should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            self.generator.generate("   ")

    @patch("services.visualization.os.environ.get")
    def test_missing_api_key_raises_runtime_error(self, mock_env_get):
        """Missing GROQ_API_KEY should raise RuntimeError."""
        mock_env_get.return_value = None

        with patch.object(
            self.generator, "_retrieve_relevant_data", return_value=["some data"]
        ):
            with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
                self.generator.generate("show me costs")

    @patch("services.visualization.query_embeddings")
    def test_retrieve_relevant_data_returns_documents(self, mock_query):
        """Data retrieval should return document chunks from ChromaDB."""
        with patch.object(
            self.generator._embedding_generator, "generate", return_value=[[0.1, 0.2, 0.3]]
        ):
            mock_query.return_value = {
                "documents": [["chunk 1", "chunk 2"]],
                "metadatas": [[{"file_name": "test.csv"}]],
            }

            result = self.generator._retrieve_relevant_data("costs breakdown")

            assert result == ["chunk 1", "chunk 2"]

    @patch("services.visualization.query_embeddings")
    def test_retrieve_relevant_data_handles_empty_results(self, mock_query):
        """Data retrieval should return empty list when no results found."""
        with patch.object(
            self.generator._embedding_generator, "generate", return_value=[[0.1, 0.2, 0.3]]
        ):
            mock_query.return_value = {"documents": [[]]}

            result = self.generator._retrieve_relevant_data("unknown query")

            assert result == []

    def test_retrieve_relevant_data_handles_exception(self):
        """Data retrieval should return empty list on failure."""
        with patch.object(
            self.generator._embedding_generator, "generate", side_effect=RuntimeError("embedding failed")
        ):
            result = self.generator._retrieve_relevant_data("test query")

            assert result == []

    def test_parse_response_valid_bar_chart(self):
        """Valid bar chart response should parse correctly."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "type": "bar",
                                "title": "Project Costs by Category",
                                "data": [
                                    {"category": "IT", "cost": 50000},
                                    {"category": "HR", "cost": 30000},
                                ],
                                "x_key": "category",
                                "y_key": "cost",
                                "name_key": None,
                                "data_key": None,
                            }
                        )
                    }
                }
            ]
        }

        result = self.generator._parse_response(response_data)

        assert isinstance(result, ChartConfig)
        assert result.type == "bar"
        assert result.title == "Project Costs by Category"
        assert len(result.data) == 2
        assert result.x_key == "category"
        assert result.y_key == "cost"

    def test_parse_response_valid_pie_chart(self):
        """Valid pie chart response should parse correctly."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "type": "pie",
                                "title": "File Distribution",
                                "data": [
                                    {"name": "PDF", "value": 10},
                                    {"name": "CSV", "value": 5},
                                ],
                                "x_key": None,
                                "y_key": None,
                                "name_key": "name",
                                "data_key": "value",
                            }
                        )
                    }
                }
            ]
        }

        result = self.generator._parse_response(response_data)

        assert isinstance(result, ChartConfig)
        assert result.type == "pie"
        assert result.name_key == "name"
        assert result.data_key == "value"

    def test_parse_response_valid_line_chart(self):
        """Valid line chart response should parse correctly."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "type": "line",
                                "title": "Monthly Spend",
                                "data": [
                                    {"month": "Jan", "spend": 1000},
                                    {"month": "Feb", "spend": 1500},
                                ],
                                "x_key": "month",
                                "y_key": "spend",
                                "name_key": None,
                                "data_key": None,
                            }
                        )
                    }
                }
            ]
        }

        result = self.generator._parse_response(response_data)

        assert isinstance(result, ChartConfig)
        assert result.type == "line"
        assert result.x_key == "month"
        assert result.y_key == "spend"

    def test_parse_response_with_markdown_fences(self):
        """Response wrapped in markdown code fences should still parse."""
        json_content = json.dumps(
            {
                "type": "line",
                "title": "Trend Over Time",
                "data": [{"month": "Jan", "value": 100}],
                "x_key": "month",
                "y_key": "value",
                "name_key": None,
                "data_key": None,
            }
        )
        response_data = {
            "choices": [
                {"message": {"content": f"```json\n{json_content}\n```"}}
            ]
        }

        result = self.generator._parse_response(response_data)

        assert isinstance(result, ChartConfig)
        assert result.type == "line"

    def test_parse_response_invalid_json_raises_value_error(self):
        """Invalid JSON in response should raise ValueError."""
        response_data = {
            "choices": [{"message": {"content": "not valid json"}}]
        }

        with pytest.raises(ValueError, match="Failed to parse"):
            self.generator._parse_response(response_data)

    def test_parse_response_missing_fields_raises_value_error(self):
        """Response missing required fields should raise ValueError."""
        response_data = {
            "choices": [
                {"message": {"content": json.dumps({"type": "bar"})}}
            ]
        }

        with pytest.raises(ValueError, match="missing required fields"):
            self.generator._parse_response(response_data)

    def test_parse_response_invalid_structure_raises_value_error(self):
        """Response with invalid structure should raise ValueError."""
        response_data = {"invalid": "structure"}

        with pytest.raises(ValueError, match="Invalid response structure"):
            self.generator._parse_response(response_data)

    def test_parse_response_invalid_chart_type_raises_value_error(self):
        """Response with invalid chart type should raise ValueError."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "type": "scatter",
                                "title": "Invalid",
                                "data": [],
                                "x_key": "x",
                                "y_key": "y",
                            }
                        )
                    }
                }
            ]
        }

        with pytest.raises(ValueError, match="missing required fields|invalid values"):
            self.generator._parse_response(response_data)

    @patch("services.visualization.httpx.Client")
    @patch("services.visualization.os.environ.get")
    @patch("services.visualization.query_embeddings")
    def test_generate_end_to_end(self, mock_query, mock_env_get, mock_httpx_client):
        """Full generate flow should produce a valid ChartConfig."""
        mock_env_get.return_value = "test-api-key"

        with patch.object(
            self.generator._embedding_generator, "generate", return_value=[[0.1, 0.2, 0.3]]
        ):
            mock_query.return_value = {
                "documents": [["Project costs: IT $50k, HR $30k"]],
            }

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "type": "bar",
                                    "title": "Costs by Department",
                                    "data": [
                                        {"dept": "IT", "cost": 50000},
                                        {"dept": "HR", "cost": 30000},
                                    ],
                                    "x_key": "dept",
                                    "y_key": "cost",
                                    "name_key": None,
                                    "data_key": None,
                                }
                            )
                        }
                    }
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.return_value = mock_response
            mock_httpx_client.return_value = mock_client_instance

            result = self.generator.generate("show project costs by department")

            assert isinstance(result, ChartConfig)
            assert result.type == "bar"
            assert result.title == "Costs by Department"
            assert len(result.data) == 2
