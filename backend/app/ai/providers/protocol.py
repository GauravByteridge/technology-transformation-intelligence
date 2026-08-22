"""
Text generation provider protocol.

Defines the contract that any LLM text generation provider must satisfy.
Implementations include Azure AI Foundry, Azure OpenAI, and Groq.
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class GenerationResult:
    """Result returned from a text generation call."""

    text: str
    model: str
    usage: dict | None = field(default=None)


class TextGenerationProvider(Protocol):
    """Protocol for LLM text generation providers.

    Any class implementing both `generate` and `stream` methods with
    matching signatures satisfies this protocol via structural subtyping.
    """

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> GenerationResult:
        """Generate a complete text response for the given prompt.

        Args:
            prompt: The user/input prompt to send to the model.
            system_prompt: Optional system-level instruction.
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)

        Returns:
            A GenerationResult containing the generated text, model name, and usage info.
        """
        ...

    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> AsyncGenerator[str, None]:
        """Stream text tokens as they are generated.

        Args:
            prompt: The user/input prompt to send to the model.
            system_prompt: Optional system-level instruction.
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)

        Yields:
            Individual text tokens/chunks as they become available.
        """
        ...
