"""
Document search service — semantic search over ingested documents.

Provides a high-level interface for searching documents by natural language
query. Generates a query embedding, performs vector similarity search,
and filters results by a configurable similarity threshold.

Designed for consumption by the Phase 5 AI agent.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.documents.pipeline import EmbeddingGenerator
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class DocumentSearchService:
    """Semantic search over ingested documents for AI agent use.

    Combines embedding generation with vector similarity search to find
    relevant document chunks matching a natural language query.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        embedding_generator: EmbeddingGenerator,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            document_repository: Repository providing vector similarity search.
            embedding_generator: Generator for converting query text to embeddings.
        """
        self._repository = document_repository
        self._embedding_generator = embedding_generator

    async def search_documents(
        self,
        project_id: UUID,
        query: str,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[dict]:
        """Search documents by natural language query with similarity filtering.

        Generates an embedding for the query text, performs cosine similarity
        search against stored document chunks, and filters results that meet
        the minimum similarity threshold.

        Args:
            project_id: UUID of the project to search within.
            query: Natural language question or search text.
            limit: Maximum number of results to return (default 10).
            threshold: Minimum similarity_score to include in results (0.0–1.0).
                Results below this threshold are excluded. Default 0.0
                (no filtering — appropriate for deterministic/mock embeddings).

        Returns:
            List of evidence dicts with: file_name, page_number, section,
            sheet_name, region, excerpt, similarity_score, document_id, chunk_id.
            Ordered by similarity_score descending (most relevant first).
        """
        # Generate query embedding
        embeddings = await self._embedding_generator.generate([query])
        query_vector = embeddings[0]

        # Perform similarity search
        raw_results = await self._repository.search_similar(
            project_id=project_id,
            query_vector=query_vector,
            limit=limit,
        )

        # Filter by threshold and transform to evidence format
        evidence_results: list[dict] = []
        for result in raw_results:
            score = result["similarity_score"]
            if score < threshold:
                continue

            evidence_results.append({
                "file_name": result["file_name"],
                "page_number": result["page_number"],
                "section": result["section"],
                "sheet_name": None,  # Set when evidence comes from Excel region
                "region": None,  # Set when evidence comes from Excel region
                "excerpt": result["chunk_content"],
                "similarity_score": score,
                "document_id": result["document_id"],
                "chunk_id": result["chunk_id"],
            })

        logger.info(
            "Document search completed",
            extra={
                "project_id": str(project_id),
                "query_length": len(query),
                "raw_results": len(raw_results),
                "filtered_results": len(evidence_results),
                "threshold": threshold,
            },
        )

        return evidence_results
