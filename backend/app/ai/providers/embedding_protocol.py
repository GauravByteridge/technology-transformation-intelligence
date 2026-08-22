"""
Embedding provider protocol.

Defines the contract that any embedding provider must satisfy.
This is architecturally independent from the text generation protocol —
a provider is not required to implement both.
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Protocol for embedding generation providers.

    Any class implementing both `embed` and `embed_batch` methods with
    matching signatures satisfies this protocol via structural subtyping.
    """

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text input.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple text inputs.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
        """
        ...
