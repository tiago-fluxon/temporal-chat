"""Base LLM adapter interface for streaming completions."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass


@dataclass
class StreamChunk:
    """Represents a single streaming token from LLM."""

    content: str
    finish_reason: str | None = None
    model: str | None = None


class BaseLLMAdapter(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def stream_completion(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream completion tokens from LLM.

        Args:
            prompt: The prompt to send to LLM
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 - 1.0)

        Yields:
            StreamChunk objects containing token content
        """
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """
        Get complete response (non-streaming).

        Args:
            prompt: The prompt to send to LLM
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 - 1.0)

        Returns:
            Complete response text
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name (e.g., 'claude', 'openai')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return default model identifier."""
        pass
