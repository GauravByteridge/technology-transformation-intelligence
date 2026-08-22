"""
Azure AI Foundry text generation provider stub.

Phase 1 will replace this stub with a full implementation
using the Azure AI Foundry SDK.
"""

from collections.abc import AsyncGenerator

from app.ai.providers.protocol import GenerationResult


class AzureFoundryTextGenerationProvider:
    """Azure AI Foundry text generation provider.

    Accepts configuration parameters to validate the DI pattern works.
    Actual implementation deferred to Phase 1.
    """

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = "",
        model: str = "",
        **kwargs: object,
    ) -> None:
        """Initialize with Azure AI Foundry configuration.

        Args:
            api_key: The API key for Azure AI Foundry.
            endpoint: The endpoint URL for the deployed model.
            model: The model deployment name.
            **kwargs: Additional provider-specific configuration.
        """
        self._api_key = api_key
        self._endpoint = endpoint
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
        raise NotImplementedError("Azure AI Foundry integration deferred to Phase 1")

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
        raise NotImplementedError("Azure AI Foundry integration deferred to Phase 1")
        # NOTE: yield is required to make this an async generator
        yield ""  # pragma: no cover
