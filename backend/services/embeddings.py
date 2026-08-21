"""
Embedding Generator Service.

Generates vector embeddings for text chunks using ChromaDB's built-in
default embedding function (based on all-MiniLM-L6-v2 via sentence-transformers).
"""

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


class EmbeddingGenerator:
    """Generates vector embeddings for text chunks.

    Uses ChromaDB's DefaultEmbeddingFunction which wraps the
    all-MiniLM-L6-v2 sentence-transformers model. This provides
    good quality embeddings without requiring separate model management.

    The generate() method handles batch processing efficiently by
    passing all texts to the embedding function in a single call.
    """

    def __init__(self):
        """Initialize the embedding generator with ChromaDB's default embedding function."""
        self._embedding_fn = DefaultEmbeddingFunction()

    def generate(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of text chunks.

        Processes all texts in a single batch call for efficiency.
        Empty or whitespace-only texts are handled gracefully.

        Args:
            texts: List of text strings to generate embeddings for.
                   Each text should be a meaningful chunk of content.

        Returns:
            List of embedding vectors (list of floats) corresponding
            to each input text, in the same order.

        Raises:
            ValueError: If texts is empty.
            RuntimeError: If embedding generation fails.
        """
        if not texts:
            raise ValueError("Cannot generate embeddings for an empty list of texts.")

        try:
            embeddings = self._embedding_fn(texts)
            # Convert numpy float32 values to plain Python floats
            return [[float(v) for v in emb] for emb in embeddings]
        except Exception as e:
            raise RuntimeError(f"Embedding generation failed: {e}") from e
