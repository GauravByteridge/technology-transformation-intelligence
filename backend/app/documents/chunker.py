"""
Text chunking implementation for the document ingestion pipeline.

Provides a simple fixed-size character chunking strategy with
configurable overlap. Satisfies the TextChunker protocol.
"""

from app.documents.pipeline import ChunkResult


class FixedSizeChunker:
    """Splits text into fixed-size character chunks with overlap.

    Satisfies the TextChunker protocol via structural subtyping.
    """

    def chunk(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list[ChunkResult]:
        """Split *text* into chunks of *chunk_size* characters with *overlap*.

        Args:
            text: Full text content to split.
            chunk_size: Target number of characters per chunk.
            overlap: Number of overlapping characters between consecutive chunks.

        Returns:
            Ordered list of ChunkResult instances with chunk_index populated.
            page_number and section are None for this basic chunker.
        """
        if not text:
            return []

        # Ensure overlap doesn't exceed chunk_size
        effective_overlap = min(overlap, chunk_size - 1) if chunk_size > 1 else 0
        step = max(chunk_size - effective_overlap, 1)

        chunks: list[ChunkResult] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            chunks.append(
                ChunkResult(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    page_number=None,
                    section=None,
                )
            )

            chunk_index += 1
            start += step

        return chunks
