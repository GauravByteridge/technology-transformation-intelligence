"""
Strands Agent Service for the Project Intelligence Hub.

Replaces the one-shot RAG pipeline with an agentic approach that can:
- Perform multiple searches iteratively
- Filter by category
- Reason step-by-step before answering
- Cite sources properly
"""

import os
import re
import logging
from typing import Optional

from strands import Agent, tool
from strands.models.litellm import LiteLLMModel

from services.embeddings import EmbeddingGenerator
from db.chroma_client import query_embeddings, get_collection_count
from db.database import SessionLocal
from models.database_models import File

logger = logging.getLogger(__name__)

# Singleton embedding generator for efficiency
_embedding_generator: Optional[EmbeddingGenerator] = None


def _get_embedding_generator() -> EmbeddingGenerator:
    """Get or create the singleton embedding generator."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator


def _get_db_session():
    """Get a database session for tool use."""
    return SessionLocal()


@tool
def search_knowledge_base(query: str, n_results: int = 8) -> str:
    """
    Search the project knowledge base for information relevant to a query.
    Returns text chunks with their source file names and categories.
    Use this tool to find specific information about project data, costs,
    audits, controls, or any topic in the uploaded files.

    Args:
        query: The search query to find relevant information. Be specific.
        n_results: Number of results to return (default 8, max 20)
    """
    n_results = min(max(n_results, 1), 20)

    try:
        embedding_gen = _get_embedding_generator()
        embedding = embedding_gen.generate([query])[0]
        results = query_embeddings(embedding, n_results=n_results)

        docs = results.get("documents", [[]])[0] or []
        metas = results.get("metadatas", [[]])[0] or []
        distances = results.get("distances", [[]])[0] or []

        if not docs:
            return "No relevant information found for this query. Try rephrasing or searching for different terms."

        # Filter by relevance (cosine distance < 0.7 is considered relevant)
        output = []
        for doc, meta, dist in zip(docs, metas, distances):
            if dist < 0.7:  # cosine distance threshold
                source = meta.get("file_name", "unknown")
                category = meta.get("category", "unknown")
                chunk_idx = meta.get("chunk_index", "?")
                output.append(
                    f"[Source: {source} | Category: {category} | Chunk: {chunk_idx} | Relevance: {1 - dist:.2f}]\n{doc}"
                )

        if not output:
            return (
                f"Found {len(docs)} results but none were sufficiently relevant (relevance < 0.3). "
                "Try more specific search terms or check if relevant files have been uploaded."
            )

        return "\n\n---\n\n".join(output)

    except Exception as e:
        logger.error(f"search_knowledge_base error: {e}")
        return f"Search failed: {str(e)}"


@tool
def get_files_by_category(category: str) -> str:
    """
    Get a list of uploaded files filtered by category.
    Use this to understand what data is available in a specific category
    before searching for detailed information.

    Args:
        category: One of: Project Costs, Burndown, Audit, IT Controls,
                  Remediation, Business Intelligence, Internal Data, Other
    """
    db = _get_db_session()
    try:
        files = db.query(File).filter(File.category == category).all()
        if not files:
            return f"No files found in category '{category}'. Available categories: Project Costs, Burndown, Audit, IT Controls, Remediation, Business Intelligence, Internal Data, Other."

        result_lines = [f"Files in category '{category}':"]
        for f in files:
            result_lines.append(
                f"  - {f.file_name} ({f.file_type}, {f.chunk_count} chunks, uploaded {f.uploaded_at.strftime('%Y-%m-%d')})"
            )
        return "\n".join(result_lines)
    finally:
        db.close()


@tool
def list_all_files() -> str:
    """
    Get a summary of all uploaded files with their categories and types.
    Use this at the start to understand what data is available before answering.
    """
    db = _get_db_session()
    try:
        files = db.query(File).all()
        if not files:
            return "No files have been uploaded yet. Ask the user to upload relevant files first."

        # Group by category
        by_category: dict[str, list[str]] = {}
        for f in files:
            cat = f.category or "Uncategorized"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f"{f.file_name} ({f.file_type})")

        result_lines = [f"Total files: {len(files)}"]
        for cat, file_list in sorted(by_category.items()):
            result_lines.append(f"\n[{cat}] ({len(file_list)} files)")
            for fname in file_list:
                result_lines.append(f"  - {fname}")

        return "\n".join(result_lines)
    finally:
        db.close()


@tool
def get_knowledge_base_stats() -> str:
    """
    Get statistics about the knowledge base: total chunks, total files.
    Useful for understanding the size and scope of available data.
    """
    db = _get_db_session()
    try:
        file_count = db.query(File).count()
        total_chunks = db.query(File).with_entities(
            db.query(File.chunk_count).as_scalar()
        ).count()

        # Get chunk count from ChromaDB
        chroma_count = get_collection_count()

        files = db.query(File).all()
        total_file_chunks = sum(f.chunk_count for f in files)

        return (
            f"Knowledge Base Statistics:\n"
            f"  - Total files: {file_count}\n"
            f"  - Total text chunks: {total_file_chunks}\n"
            f"  - Indexed vectors in ChromaDB: {chroma_count}"
        )
    finally:
        db.close()


SYSTEM_PROMPT = """You are a senior project data analyst with access to a knowledge base of uploaded project files (PDFs, Excel spreadsheets, CSVs, and JSON files).

Your job is to interpret project data and provide clear, insightful answers. Follow these rules:

BEFORE ANSWERING:
1. ALWAYS use the search_knowledge_base tool to find relevant information first
2. If results seem incomplete, search again with different terms
3. Use list_all_files to understand what data is available
4. Use get_files_by_category to find category-specific information

WHEN ANSWERING:
1. INTERPRET the data — don't just dump raw numbers. Explain what they mean.
2. SUMMARIZE key findings first, then provide details if relevant.
3. Use TABLES for structured data when it helps clarity.
4. CALCULATE totals, averages, trends, and percentages when useful.
5. HIGHLIGHT important insights (risks, anomalies, trends).
6. If data contains categories (costs, audit findings, controls), group and summarize by category.
7. Use bullet points for readability.
8. CITE your sources by mentioning the file names.
9. If the data is insufficient to fully answer, say what's missing.
10. Answer in a professional tone suitable for executive stakeholders.
11. Only use information from the search results — never make up data.

If no relevant data is found after searching, clearly state that and suggest what files the user should upload."""


class StrandsRAGAgent:
    """Wrapper class for the Strands-based RAG agent."""

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        model_id: str = "groq/llama-3.3-70b-versatile",
    ):
        """
        Initialize the Strands RAG agent.

        Args:
            groq_api_key: Groq API key. If None, reads from GROQ_API_KEY env variable.
            model_id: LiteLLM model identifier (default: groq/llama-3.3-70b-versatile)
        """
        self._api_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
        self._model_id = model_id
        self._agent: Optional[Agent] = None

    def _build_agent(self) -> Agent:
        """Build and return the Strands agent."""
        if not self._api_key:
            raise RuntimeError(
                "Groq API key is not configured. "
                "Set the GROQ_API_KEY environment variable."
            )

        model = LiteLLMModel(
            model_id=self._model_id,
            params={
                "temperature": 0.3,
                "max_tokens": 4096,
                "api_key": self._api_key,
            },
        )

        return Agent(
            model=model,
            tools=[
                search_knowledge_base,
                get_files_by_category,
                list_all_files,
                get_knowledge_base_stats,
            ],
            system_prompt=SYSTEM_PROMPT,
        )

    def query(self, question: str) -> dict:
        """
        Process a question using the Strands agent.

        Args:
            question: The user's natural language question.

        Returns:
            Dict with 'answer' (str) and 'sources' (list of file names).
        """
        agent = self._build_agent()

        try:
            result = agent(question)
            answer = str(result)

            # Extract source file names from the conversation
            sources = self._extract_sources(result, answer)

            return {
                "answer": answer,
                "sources": list(sources),
            }

        except Exception as e:
            logger.error(f"Strands agent error: {e}")
            raise RuntimeError(f"AI agent failed: {str(e)}") from e

    def _extract_sources(self, result, answer: str) -> set[str]:
        """Extract source file names from agent result and answer text."""
        sources = set()

        # Pattern to match [Source: filename ...] in the answer
        source_pattern = r'\[Source:\s*([^\|\]]+)'
        for match in re.findall(source_pattern, answer):
            sources.add(match.strip())

        # Also check message history if available
        if hasattr(result, "message_history") and result.message_history:
            for msg in result.message_history:
                if hasattr(msg, "content"):
                    content = msg.content
                    if isinstance(content, list):
                        for block in content:
                            if hasattr(block, "text") and block.text:
                                for match in re.findall(source_pattern, block.text):
                                    sources.add(match.strip())
                    elif isinstance(content, str):
                        for match in re.findall(source_pattern, content):
                            sources.add(match.strip())

        return sources
