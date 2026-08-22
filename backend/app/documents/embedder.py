"""
Deterministic embedding generator for the document ingestion pipeline.

Uses SHA-256 hashing to produce repeatable vectors of exactly
EMBEDDING_DIMENSION length. This stub does NOT call any external
service — it is purely local computation for Phase 0 smoke testing.

Full embedding generation delegating to a real model is deferred to Phase 1.
"""

import hashlib
import struct

from app.ai.providers.embedding_protocol import EmbeddingProvider

# Default dimension matching the project configuration
DEFAULT_EMBEDDING_DIMENSION = 1536


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
