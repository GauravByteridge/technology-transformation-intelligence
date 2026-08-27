"""
Embedding generators for the document ingestion pipeline.

Provides two implementations:
- DeterministicEmbeddingGenerator: Hash-based stub for testing/demo (no external calls).
- ProductionEmbeddingGenerator: Real embeddings via configured EmbeddingProvider.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import struct

from app.ai.providers.embedding_protocol import EmbeddingProvider
from app.errors.document_errors import EmbeddingGenerationError

logger = logging.getLogger(__name__)

# Default dimension matching the project configuration
DEFAULT_EMBEDDING_DIMENSION = 384

# Maximum number of texts per batch call to the provider
_MAX_BATCH_SIZE = 100

# Timeout for embedding provider calls (seconds)
_PROVIDER_TIMEOUT_SECONDS = 30


class DeterministicEmbeddingGenerator:
    """Generates deterministic embedding vectors using a hash-based approach.

    Satisfies the EmbeddingGenerator protocol via structural subtyping.
    Delegates conceptually to the EmbeddingProvider interface but does not
    invoke a real model — instead produces repeatable vectors locally.

    Each unique text input always produces the SAME embedding vector.
    Vector length exactly matches the configured EMBEDDING_DIMENSION.
    """

    def __init__(
        self,
        embedding_dimension: int = DEFAULT_EMBEDDING_DIMENSION,
        provider: EmbeddingProvider | None = None,
    ) -> None:
        """Initialize the generator.

        Args:
            embedding_dimension: Length of the output embedding vectors.
            provider: Optional EmbeddingProvider for future delegation.
                      Not invoked in this Phase 0 stub.
        """
        self._dimension = embedding_dimension
        self._provider = provider

    @property
    def dimension(self) -> int:
        """The dimension of embedding vectors this generator produces."""
        return self._dimension

    async def generate(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic embeddings for the provided text segments.

        Uses SHA-256 of each text to seed iterative hashing, producing
        a vector of exactly `embedding_dimension` floats in the range [0, 1).

        Args:
            texts: List of text segments to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        return [self._hash_to_vector(text) for text in texts]

    def _hash_to_vector(self, text: str) -> list[float]:
        """Convert text to a deterministic float vector via iterative SHA-256.

        The approach:
        1. Compute SHA-256 of the input text (32 bytes).
        2. Extract floats from the hash bytes (4 bytes → 1 float via unsigned int).
        3. If more floats are needed, hash the previous digest to get more bytes.
        4. Normalize each value to [0, 1) range.

        This guarantees identical input → identical output, with vectors of
        exactly self._dimension length.
        """
        vector: list[float] = []
        digest = hashlib.sha256(text.encode("utf-8")).digest()

        while len(vector) < self._dimension:
            # Each 32-byte digest yields 8 floats (4 bytes per float)
            for i in range(0, 32, 4):
                if len(vector) >= self._dimension:
                    break
                # Unpack 4 bytes as unsigned 32-bit int, normalize to [0, 1)
                value = struct.unpack(">I", digest[i : i + 4])[0]
                vector.append(value / 0xFFFFFFFF)

            # Chain-hash to produce more bytes if needed
            digest = hashlib.sha256(digest).digest()

        return vector


class ProductionEmbeddingGenerator:
    """Real embedding generator that delegates to the configured EmbeddingProvider.

    Satisfies the EmbeddingGenerator protocol. Calls the provider's embed_batch()
    method with batching (max 100 texts per call), dimension validation, and
    timeout handling.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        embedding_dimension: int = DEFAULT_EMBEDDING_DIMENSION,
    ) -> None:
        """Initialize with a real embedding provider.

        Args:
            embedding_provider: The provider implementing embed_batch().
            embedding_dimension: Expected dimension of output vectors.
                Used for validation after provider returns.
        """
        self._provider = embedding_provider
        self._dimension = embedding_dimension

    @property
    def dimension(self) -> int:
        """The expected dimension of embedding vectors."""
        return self._dimension

    async def generate(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings by delegating to the configured provider.

        Batches texts in groups of up to 100, applies a 30-second timeout,
        and validates output dimensions.

        Args:
            texts: List of text segments to embed.

        Returns:
            List of embedding vectors, one per input text.

        Raises:
            EmbeddingGenerationError: If the provider fails, times out,
                or returns vectors with incorrect dimensions.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # Process in batches of _MAX_BATCH_SIZE
        for batch_start in range(0, len(texts), _MAX_BATCH_SIZE):
            batch = texts[batch_start : batch_start + _MAX_BATCH_SIZE]

            try:
                batch_embeddings = await asyncio.wait_for(
                    self._provider.embed_batch(batch),
                    timeout=_PROVIDER_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                raise EmbeddingGenerationError(
                    file_name="<batch>",
                    message=(
                        f"Embedding provider timed out after {_PROVIDER_TIMEOUT_SECONDS}s "
                        f"processing batch of {len(batch)} texts"
                    ),
                    detail=f"Batch starting at index {batch_start}",
                )
            except EmbeddingGenerationError:
                raise
            except Exception as exc:
                provider_name = type(self._provider).__name__
                raise EmbeddingGenerationError(
                    file_name="<batch>",
                    message=(
                        f"Embedding provider '{provider_name}' failed: {exc}"
                    ),
                    detail=str(exc),
                ) from exc

            # Validate output dimensions
            for idx, embedding in enumerate(batch_embeddings):
                if len(embedding) != self._dimension:
                    raise EmbeddingGenerationError(
                        file_name="<batch>",
                        message=(
                            f"Embedding dimension mismatch: expected {self._dimension}, "
                            f"got {len(embedding)} at index {batch_start + idx}"
                        ),
                        detail=(
                            f"Provider returned vector of length {len(embedding)} "
                            f"but EMBEDDING_DIMENSION is configured as {self._dimension}"
                        ),
                    )

            all_embeddings.extend(batch_embeddings)

        return all_embeddings
