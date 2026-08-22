"""
Mock text generation and embedding providers.

Provides deterministic, canned responses for smoke-testing
the full AI orchestration path without external API calls.
Phase 1 will replace this with real provider integrations.
"""

from collections.abc import AsyncGenerator

from app.ai.providers.protocol import GenerationResult

MOCK_MODEL = "mock-v1"
MOCK_EMBEDDING_DIMENSION = 1536

MOCK_RESPONSE = (
    "This is a mock response from the MockTextGenerationProvider. "
    "In Phase 1, this will be replaced with real LLM integration."
)


class MockTextGenerationProvider:
    """Deterministic text generation provider for smoke testing.

    Returns canned responses without making any external API calls.
    Useful for verifying the full orchestration path works end-to-end
    in Demo Mode without requiring LLM credentials.
    """

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> GenerationResult:
        """Return a deterministic canned response.

        Args:
            prompt: The user/input prompt (not used in mock).
            system_prompt: Optional system-level instruction (not used in mock).
            **kwargs: Provider-specific parameters (ignored).

        Returns:
            A GenerationResult with the canned mock response.
        """
        return GenerationResult(
            text=MOCK_RESPONSE,
            model=MOCK_MODEL,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> AsyncGenerator[str, None]:
        """Yield the mock response split into word-level chunks.

        Args:
            prompt: The user/input prompt (not used in mock).
            system_prompt: Optional system-level instruction (not used in mock).
            **kwargs: Provider-specific parameters (ignored).

        Yields:
            Individual words from the canned response, space-separated.
        """
        words = MOCK_RESPONSE.split(" ")
        for i, word in enumerate(words):
            # Add space before words except the first
            yield word if i == 0 else f" {word}"


class MockEmbeddingProvider:
    """Deterministic embedding provider for smoke testing.

    Returns zero-vector embeddings of the configured dimension without
    making any external API calls. Useful for verifying the embedding
    pipeline works end-to-end in Demo Mode.
    """

    def __init__(self, dimension: int = MOCK_EMBEDDING_DIMENSION, **kwargs: object) -> None:
        """Initialize with the target embedding dimension.

        Args:
            dimension: The embedding vector dimension to produce.
            **kwargs: Additional configuration (ignored).
        """
        self._dimension = dimension

    async def embed(self, text: str) -> list[float]:
        """Return a deterministic zero-vector embedding.

        Args:
            text: The text to embed (content not used in mock).

        Returns:
            A list of floats with the configured dimension, all zeros.
        """
        return [0.0] * self._dimension

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return deterministic zero-vector embeddings for each input.

        Args:
            texts: A list of texts to embed (content not used in mock).

        Returns:
            A list of zero-vector embeddings, one per input text.
        """
        return [[0.0] * self._dimension for _ in texts]
