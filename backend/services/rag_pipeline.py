"""
RAG Pipeline Service.

Orchestrates retrieval-augmented generation for chat queries:
1. Generates an embedding for the user's question
2. Searches ChromaDB for the most relevant document chunks
3. Constructs a prompt combining retrieved context and the question
4. Sends the prompt to the Groq API for inference
5. Returns the answer with source file attributions
"""

import os
import logging
from typing import Optional

import httpx

from services.embeddings import EmbeddingGenerator
from db.chroma_client import query_embeddings
from models.schemas import ChatResponse

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"


class RAGPipeline:
    """Orchestrates retrieval and generation for chat queries.

    Uses an EmbeddingGenerator for question vectorization, ChromaDB for
    similarity search, and the Groq API (OpenAI-compatible) for LLM inference.
    """

    def __init__(
        self,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        groq_api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ):
        """Initialize the RAG pipeline.

        Args:
            embedding_generator: Instance of EmbeddingGenerator for vectorizing questions.
                                 If None, a new instance is created.
            groq_api_key: Groq API key. If None, reads from GROQ_API_KEY env variable.
            model: The Groq model to use for inference.
        """
        self._embedding_generator = embedding_generator or EmbeddingGenerator()
        self._groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
        self._model = model

    def query(self, question: str, top_k: int = 10) -> ChatResponse:
        """Process a question and return an answer with sources.

        Steps:
            1. Generate embedding for the question
            2. Search ChromaDB for top_k most similar chunks
            3. Construct a prompt with retrieved context
            4. Call Groq API for inference
            5. Return answer and source file names

        Args:
            question: The user's natural language question.
            top_k: Number of similar chunks to retrieve (default: 5).

        Returns:
            ChatResponse with the generated answer and list of source file names.

        Raises:
            RuntimeError: If the Groq API call fails or returns an error.
        """
        # Step 1: Generate embedding for the question
        question_embedding = self._generate_question_embedding(question)

        # Step 2: Search ChromaDB for relevant chunks
        search_results = self._search_similar_chunks(question_embedding, top_k)

        # Step 3: Extract context and sources from results
        context_chunks, source_files = self._extract_context_and_sources(search_results)

        # Handle case where no relevant chunks are found
        if not context_chunks:
            return ChatResponse(
                answer="No relevant information was found in the project data. "
                       "Please upload files related to your question.",
                sources=[],
            )

        # Step 4: Construct the prompt
        prompt = self.build_prompt(question, context_chunks)

        # Step 5: Call Groq API for inference
        answer = self._call_groq_api(prompt)

        return ChatResponse(
            answer=answer,
            sources=list(source_files),
        )

    def _generate_question_embedding(self, question: str) -> list[float]:
        """Generate an embedding vector for the user's question.

        Args:
            question: The user's question text.

        Returns:
            List of floats representing the question embedding.
        """
        embeddings = self._embedding_generator.generate([question])
        return embeddings[0]

    def _search_similar_chunks(
        self, query_embedding: list[float], top_k: int
    ) -> dict:
        """Search ChromaDB for the most similar document chunks.

        Args:
            query_embedding: Vector representation of the question.
            top_k: Number of results to return.

        Returns:
            ChromaDB query results dict with ids, documents, metadatas, distances.
        """
        return query_embeddings(query_embedding=query_embedding, n_results=top_k)

    def _extract_context_and_sources(
        self, search_results: dict
    ) -> tuple[list[str], set[str]]:
        """Extract context text and source file names from search results.

        Args:
            search_results: ChromaDB query results.

        Returns:
            Tuple of (list of context chunk texts, set of source file names).
        """
        context_chunks: list[str] = []
        source_files: set[str] = set()

        documents = search_results.get("documents", [[]])
        metadatas = search_results.get("metadatas", [[]])

        # ChromaDB returns nested lists (one per query embedding)
        if documents and documents[0]:
            for doc in documents[0]:
                if doc:
                    context_chunks.append(doc)

        if metadatas and metadatas[0]:
            for metadata in metadatas[0]:
                if metadata and "file_name" in metadata:
                    source_files.add(metadata["file_name"])

        return context_chunks, source_files

    def build_prompt(self, question: str, context_chunks: list[str]) -> str:
        """Construct the RAG prompt combining context and the user question.

        The prompt clearly separates context from the question and instructs
        the LLM to answer based on the provided context.

        Args:
            question: The user's original question.
            context_chunks: List of relevant text chunks from the knowledge base.

        Returns:
            Formatted prompt string ready for LLM inference.
        """
        context_text = "\n\n---\n\n".join(context_chunks)

        prompt = (
            "=== CONTEXT ===\n\n"
            f"{context_text}\n\n"
            "=== END CONTEXT ===\n\n"
            "=== QUESTION ===\n\n"
            f"{question}\n\n"
            "=== END QUESTION ===\n\n"
            "Provide a clear, well-structured answer based on the context above."
        )
        return prompt

    def _call_groq_api(self, prompt: str) -> str:
        """Send the constructed prompt to the Groq API for inference.

        Uses the OpenAI-compatible chat completions endpoint.

        Args:
            prompt: The fully constructed RAG prompt.

        Returns:
            The generated answer text from the LLM.

        Raises:
            RuntimeError: If the API key is missing, or the API call fails.
        """
        if not self._groq_api_key:
            raise RuntimeError(
                "Groq API key is not configured. "
                "Set the GROQ_API_KEY environment variable."
            )

        headers = {
            "Authorization": f"Bearer {self._groq_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior project data analyst. Your job is to interpret project data "
                        "and provide clear, insightful answers. Follow these rules:\n\n"
                        "1. INTERPRET the data — don't just dump raw numbers. Explain what they mean.\n"
                        "2. SUMMARIZE key findings first, then provide details if relevant.\n"
                        "3. Use TABLES for structured data when it helps clarity.\n"
                        "4. CALCULATE totals, averages, trends, and percentages when useful.\n"
                        "5. HIGHLIGHT important insights (risks, anomalies, trends).\n"
                        "6. If data contains categories (costs, audit findings, controls), "
                        "group and summarize by category.\n"
                        "7. Use bullet points for readability.\n"
                        "8. If the data is insufficient to fully answer, say what's missing.\n"
                        "9. Answer in a professional tone suitable for executive stakeholders.\n"
                        "10. Only use information from the provided context — never make up data."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    GROQ_API_URL,
                    headers=headers,
                    json=payload,
                )

            if response.status_code != 200:
                logger.error(
                    "Groq API returned status %d: %s",
                    response.status_code,
                    response.text,
                )
                raise RuntimeError(
                    f"AI service returned an error (status {response.status_code}). "
                    "Please try again later."
                )

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError(
                    "AI service returned an empty response. Please try again."
                )

            return (choices[0]["message"].get("content") or choices[0]["message"].get("reasoning", "")).strip()

        except httpx.TimeoutException:
            logger.error("Groq API request timed out")
            raise RuntimeError(
                "AI service request timed out. Please try again later."
            )
        except httpx.RequestError as e:
            logger.error("Groq API request failed: %s", str(e))
            raise RuntimeError(
                "AI service is unavailable. Please check your connection and try again."
            )
