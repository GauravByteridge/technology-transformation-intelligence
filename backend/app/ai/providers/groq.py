"""
Groq text generation provider stub.

Phase 1 will replace this stub with a full implementation
using the Groq SDK.
"""

from collections.abc import AsyncGenerator

from app.ai.providers.protocol import GenerationResult


class GroqTextGenerationProvider:
    """Groq text generation provider.

    Accepts configuration parameters to validate the DI pattern works.
    Actual implementation deferred to Phase 1.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        **kwargs: object,
    ) -> None:
        """Initialize with Groq configuration.

        Args:
            api_key: The API key for the Groq API.
            model: The model name to use (e.g. "llama3-70b-8192").
            **kwargs: Additional provider-specific configuration.
        """
        self._api_key = api_key
        self._model = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> GenerationResult:
        """Not implemented — deferred to Phase 1.

        Raises:
            NotImplementedError: Always, until Phase 1 integration.
        """
        raise NotImplementedError("Groq integration deferred to Phase 1")

    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> AsyncGenerator[str, None]:
        """Not implemented — deferred to Phase 1.

        Raises:
            NotImplementedError: Always, until Phase 1 integration.
        """
        raise NotImplementedError("Groq integration deferred to Phase 1")
        # NOTE: yield is required to make this an async generator
        yield ""  # pragma: no cover
