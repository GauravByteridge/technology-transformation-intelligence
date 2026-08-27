"""
Sentence-Transformers embedding provider.

Uses a local sentence-transformers model (all-MiniLM-L6-v2 by default)
to generate embeddings without any external API calls.

Produces 384-dimensional vectors suitable for cosine similarity search.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded model instance (singleton)
_model_instance: Any = None
_model_name: str = ""


def _get_model(model_name: str) -> Any:
    """Lazily load and cache the SentenceTransformer model."""
    global _model_instance, _model_name

    if _model_instance is not None and _model_name == model_name:
        return _model_instance

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise RuntimeError(
            "sentence-transformers is required for SentenceTransformerEmbeddingProvider. "
            "Install it with: pip install sentence-transformers"
        )

    logger.info("Loading sentence-transformers model: %s", model_name)
    _model_instance = SentenceTransformer(model_name)
    _model_name = model_name
    logger.info("Model loaded: %s (dimension: %d)", model_name, _model_instance.get_sentence_embedding_dimension())
    return _model_instance


class SentenceTransformerEmbeddingProvider:
    """Local embedding provider using sentence-transformers.

    Satisfies the EmbeddingProvider protocol via structural subtyping.
    No external API calls — runs inference locally on CPU.

    Default model: all-MiniLM-L6-v2 (384 dimensions, fast, good quality)
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", **kwargs: Any) -> None:
        """Initialize provider with model name.

        Args:
            model_name: Name of the sentence-transformers model to use.
            **kwargs: Ignored (for compatibility with provider registry).
        """
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        """Return the embedding dimension of the loaded model."""
        model = _get_model(self._model_name)
        return model.get_sentence_embedding_dimension()

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text input.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            model = _get_model(self._model_name)
            dim = model.get_sentence_embedding_dimension()
            return [0.0] * dim

        model = _get_model(self._model_name)
        embedding = model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Filters out empty/whitespace-only texts (returns zero vectors for those),
        batches the rest through the model in a single call.

        Args:
            texts: List of text segments to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        if not texts:
            return []

        model = _get_model(self._model_name)
        dim = model.get_sentence_embedding_dimension()

        # Identify which texts are non-empty
        results: list[list[float]] = []
        non_empty_indices: list[int] = []
        non_empty_texts: list[str] = []

        for i, text in enumerate(texts):
            if text and text.strip():
                non_empty_indices.append(i)
                non_empty_texts.append(text)

        # Generate embeddings for non-empty texts in one batch
        if non_empty_texts:
            embeddings = model.encode(non_empty_texts, normalize_embeddings=True)
            embedding_map = {
                non_empty_indices[j]: embeddings[j].tolist()
                for j in range(len(non_empty_texts))
            }
        else:
            embedding_map = {}

        # Build final result list, zero vector for empty texts
        zero_vector = [0.0] * dim
        for i in range(len(texts)):
            if i in embedding_map:
                results.append(embedding_map[i])
            else:
                results.append(zero_vector)

        return results
