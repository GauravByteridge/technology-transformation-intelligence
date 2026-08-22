"""
Provider registry for resolving text generation and embedding providers.

Maintains two separate registries so that a provider class is not
required to implement both text generation and embedding capabilities.
"""

from app.ai.providers.embedding_protocol import EmbeddingProvider
from app.ai.providers.protocol import TextGenerationProvider
from app.errors.ai_errors import ProviderResolutionError


class ProviderRegistry:
    """Registry that maps provider names to their implementation classes.

    Supports separate registration and resolution for text generation
    providers and embedding providers. A single class may be registered
    in both registries if it implements both protocols.
    """

    def __init__(self) -> None:
        self._text_providers: dict[str, type[TextGenerationProvider]] = {}
        self._embedding_providers: dict[str, type[EmbeddingProvider]] = {}

    def register_text_provider(
        self, name: str, provider_class: type[TextGenerationProvider]
    ) -> None:
        """Register a text generation provider class under the given name.

        Args:
            name: Identifier for the provider (e.g. "azure_openai", "groq").
            provider_class: The class implementing TextGenerationProvider.
        """
        self._text_providers[name] = provider_class

    def register_embedding_provider(
        self, name: str, provider_class: type[EmbeddingProvider]
    ) -> None:
        """Register an embedding provider class under the given name.

        Args:
            name: Identifier for the provider (e.g. "azure_openai").
            provider_class: The class implementing EmbeddingProvider.
        """
        self._embedding_providers[name] = provider_class

    def resolve_text_provider(self, name: str, **config: object) -> TextGenerationProvider:
        """Instantiate and return a text generation provider by name.

        Args:
            name: The registered provider name.
            **config: Configuration passed to the provider constructor.

        Returns:
            An instance of the resolved text generation provider.

        Raises:
            ProviderResolutionError: If the name is not registered.
        """
        provider_class = self._text_providers.get(name)
        if provider_class is None:
            raise ProviderResolutionError(
                provider_name=name,
                supported_providers=self.list_text_providers(),
            )
        return provider_class(**config)  # type: ignore[call-arg]

    def resolve_embedding_provider(self, name: str, **config: object) -> EmbeddingProvider:
        """Instantiate and return an embedding provider by name.

        Args:
            name: The registered provider name.
            **config: Configuration passed to the provider constructor.

        Returns:
            An instance of the resolved embedding provider.

        Raises:
            ProviderResolutionError: If the name is not registered.
        """
        provider_class = self._embedding_providers.get(name)
        if provider_class is None:
            raise ProviderResolutionError(
                provider_name=name,
                supported_providers=self.list_embedding_providers(),
            )
        return provider_class(**config)  # type: ignore[call-arg]

    def list_text_providers(self) -> list[str]:
        """Return the names of all registered text generation providers."""
        return list(self._text_providers.keys())

    def list_embedding_providers(self) -> list[str]:
        """Return the names of all registered embedding providers."""
        return list(self._embedding_providers.keys())
