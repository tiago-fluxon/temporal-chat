"""OpenAI LLM adapter with streaming support."""

from collections.abc import AsyncGenerator

import openai

from .base import BaseLLMAdapter, StreamChunk


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI API with streaming."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        """
        Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key
            model: OpenAI model identifier
        """
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model

    async def stream_completion(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream completion tokens from OpenAI.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 - 1.0)

        Yields:
            StreamChunk objects with token content
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        stream = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                yield StreamChunk(
                    content=delta.content,
                    finish_reason=chunk.choices[0].finish_reason,
                    model=chunk.model,
                )

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """
        Get complete response (non-streaming).

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 - 1.0)

        Returns:
            Complete response text
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "openai"

    @property
    def default_model(self) -> str:
        """Return default model identifier."""
        return self.model
