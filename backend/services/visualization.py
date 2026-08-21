"""
Visualization Generator Service.

Generates chart configurations from natural language queries by:
1. Retrieving relevant data from ChromaDB
2. Sending data + query to Groq API for chart type determination and data mapping
3. Parsing the LLM response into a ChartConfig model
"""

import json
import os
import logging

import httpx

from models.schemas import ChartConfig
from services.embeddings import EmbeddingGenerator
from db.chroma_client import query_embeddings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are a data visualization assistant. Given a user query and relevant data context, 
you must determine the most appropriate chart type and produce a JSON chart configuration.

You MUST respond with ONLY a valid JSON object (no markdown, no explanation) in this exact format:
{
  "type": "bar" | "line" | "pie",
  "title": "A descriptive chart title",
  "data": [{"label": "...", "value": ...}, ...],
  "x_key": "key for x-axis (for bar/line charts)",
  "y_key": "key for y-axis values (for bar/line charts)",
  "name_key": "key for segment names (for pie charts)",
  "data_key": "key for segment values (for pie charts)"
}

Rules:
- For bar and line charts: include x_key and y_key, set name_key and data_key to null
- For pie charts: include name_key and data_key, set x_key and y_key to null
- The "data" array must contain objects with keys matching x_key/y_key or name_key/data_key
- Extract or synthesize realistic data from the provided context
- Choose the chart type that best represents the data for the user's query
- If the context doesn't contain enough data, create a reasonable representation based on what's available
"""


class VisualizationGenerator:
    """Generates chart configurations from natural language queries.

    Uses ChromaDB for data retrieval and Groq API for determining
    chart type and mapping data fields appropriately.
    """

    def __init__(self):
        """Initialize the visualization generator with embedding generator."""
        self._embedding_generator = EmbeddingGenerator()

    def generate(self, query: str) -> ChartConfig:
        """Generate chart configuration from a natural language query.

        Retrieves relevant data from ChromaDB, sends it to Groq API
        to determine the appropriate chart type and data mapping,
        then parses the response into a ChartConfig.

        Args:
            query: Natural language query describing the desired visualization.

        Returns:
            ChartConfig with type, title, data, and key mappings.

        Raises:
            ValueError: If the query is empty or the LLM response cannot be parsed.
            RuntimeError: If Groq API call fails or returns an unusable response.
        """
        if not query or not query.strip():
            raise ValueError("Visualization query cannot be empty.")

        # Step 1: Retrieve relevant data from ChromaDB
        context_chunks = self._retrieve_relevant_data(query)

        # Step 2: Call Groq API with context and query
        chart_config = self._generate_chart_config(query, context_chunks)

        return chart_config

    def _retrieve_relevant_data(self, query: str) -> list[str]:
        """Retrieve relevant data chunks from ChromaDB using semantic search.

        Args:
            query: The user's visualization query.

        Returns:
            List of relevant text chunks from the vector store.
        """
        try:
            query_embedding = self._embedding_generator.generate([query])[0]
            results = query_embeddings(query_embedding, n_results=5)

            documents = results.get("documents", [[]])[0]
            return documents if documents else []
        except Exception as e:
            logger.warning(f"Failed to retrieve data from ChromaDB: {e}")
            return []

    def _generate_chart_config(self, query: str, context_chunks: list[str]) -> ChartConfig:
        """Call Groq API to determine chart type and data mapping.

        Args:
            query: The user's visualization query.
            context_chunks: Retrieved data chunks for context.

        Returns:
            Parsed ChartConfig from the LLM response.

        Raises:
            RuntimeError: If the Groq API call fails.
            ValueError: If the response cannot be parsed into a valid ChartConfig.
        """
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set.")

        # Build user message with context and query
        context_text = "\n\n".join(context_chunks) if context_chunks else "No data available."
        user_message = (
            f"Data Context:\n{context_text}\n\n"
            f"User Query: {query}\n\n"
            "Generate the chart configuration JSON."
        )

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.2,
            "max_tokens": 1024,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(GROQ_API_URL, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API returned error status: {e.response.status_code}")
            raise RuntimeError(
                f"Groq API request failed with status {e.response.status_code}."
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Groq API request failed: {e}")
            raise RuntimeError("Failed to connect to Groq API.") from e

        # Parse the LLM response
        return self._parse_response(response.json())

    def _parse_response(self, response_data: dict) -> ChartConfig:
        """Parse the Groq API response into a ChartConfig.

        Args:
            response_data: The JSON response from Groq API.

        Returns:
            Validated ChartConfig instance.

        Raises:
            ValueError: If the response cannot be parsed into a valid chart config.
        """
        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError("Invalid response structure from Groq API.") from e

        # Clean up the content - strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = content.index("\n")
            content = content[first_newline + 1:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            config_dict = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse chart configuration from LLM response: {e}"
            ) from e

        # Validate and construct ChartConfig
        try:
            chart_config = ChartConfig(
                type=config_dict["type"],
                title=config_dict["title"],
                data=config_dict["data"],
                x_key=config_dict.get("x_key"),
                y_key=config_dict.get("y_key"),
                data_key=config_dict.get("data_key"),
                name_key=config_dict.get("name_key"),
            )
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"LLM response missing required fields or has invalid values: {e}"
            ) from e

        return chart_config
