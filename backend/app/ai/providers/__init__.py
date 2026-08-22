"""
AI provider protocols, registry, and implementations.

Exports the text generation and embedding provider protocols,
the provider registry for resolving providers by name,
shared result types, and all provider implementations.
"""

from app.ai.providers.azure_foundry import AzureFoundryTextGenerationProvider
from app.ai.providers.azure_openai import (
    AzureOpenAIEmbeddingProvider,
    AzureOpenAITextGenerationProvider,
)
from app.ai.providers.embedding_protocol import EmbeddingProvider
from app.ai.providers.groq import GroqTextGenerationProvider
from app.ai.providers.mock_provider import MockEmbeddingProvider, MockTextGenerationProvider
from app.ai.providers.protocol import GenerationResult, TextGenerationProvider
from app.ai.providers.registry import ProviderRegistry

__all__ = [
    "AzureFoundryTextGenerationProvider",
    "AzureOpenAIEmbeddingProvider",
    "AzureOpenAITextGenerationProvider",
    "EmbeddingProvider",
    "GenerationResult",
    "GroqTextGenerationProvider",
    "MockEmbeddingProvider",
    "MockTextGenerationProvider",
    "ProviderRegistry",
    "TextGenerationProvider",
]
