"""Claude (Anthropic) LLM adapter with streaming support."""

from collections.abc import AsyncGenerator

import anthropic

from .base import BaseLLMAdapter, StreamChunk


class ClaudeAdapter(BaseLLMAdapter):
    """Adapter for Anthropic's Claude API with streaming."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Claude adapter.

        Args:
            api_key: Anthropic API key
            model: Claude model identifier
        """
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def stream_completion(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream completion tokens from Claude.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 - 1.0)

        Yields:
            StreamChunk objects with token content
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text_event in stream.text_stream:
                yield StreamChunk(
                    content=text_event,
                    model=self.model,
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

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "claude"

    @property
    def default_model(self) -> str:
        """Return default model identifier."""
        return self.model
