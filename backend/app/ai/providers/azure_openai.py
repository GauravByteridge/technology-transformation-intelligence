"""
Azure OpenAI text generation and embedding provider stub.

Phase 1 will replace this stub with a full implementation
using the Azure OpenAI SDK.
"""

from collections.abc import AsyncGenerator

from app.ai.providers.protocol import GenerationResult


class AzureOpenAITextGenerationProvider:
    """Azure OpenAI text generation provider.

    Accepts configuration parameters to validate the DI pattern works.
    Actual implementation deferred to Phase 1.
    """

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = "",
        model: str = "",
        api_version: str = "",
        **kwargs: object,
    ) -> None:
        """Initialize with Azure OpenAI configuration.

        Args:
            api_key: The API key for Azure OpenAI.
            endpoint: The Azure OpenAI resource endpoint.
            model: The deployment name for the model.
            api_version: The API version to use.
            **kwargs: Additional provider-specific configuration.
        """
        self._api_key = api_key
        self._endpoint = endpoint
        self._model = model
        self._api_version = api_version

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
        raise NotImplementedError("Azure OpenAI integration deferred to Phase 1")

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
        raise NotImplementedError("Azure OpenAI integration deferred to Phase 1")
        # NOTE: yield is required to make this an async generator
        yield ""  # pragma: no cover


class AzureOpenAIEmbeddingProvider:
    """Azure OpenAI embedding provider.

    Accepts configuration parameters to validate the DI pattern works.
    Actual implementation deferred to Phase 1.
    """

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = "",
        model: str = "",
        api_version: str = "",
        **kwargs: object,
    ) -> None:
        """Initialize with Azure OpenAI embedding configuration.

        Args:
            api_key: The API key for Azure OpenAI.
            endpoint: The Azure OpenAI resource endpoint.
            model: The embedding deployment name.
            api_version: The API version to use.
            **kwargs: Additional provider-specific configuration.
        """
        self._api_key = api_key
        self._endpoint = endpoint
        self._model = model
        self._api_version = api_version

    async def embed(self, text: str) -> list[float]:
        """Not implemented — deferred to Phase 1.

        Raises:
            NotImplementedError: Always, until Phase 1 integration.
        """
        raise NotImplementedError("Azure OpenAI embedding integration deferred to Phase 1")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Not implemented — deferred to Phase 1.

        Raises:
            NotImplementedError: Always, until Phase 1 integration.
        """
        raise NotImplementedError("Azure OpenAI embedding integration deferred to Phase 1")
