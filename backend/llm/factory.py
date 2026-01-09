"""Factory for creating LLM adapter instances."""

import os

from .base import BaseLLMAdapter
from .claude_adapter import ClaudeAdapter
from .openai_adapter import OpenAIAdapter


class LLMProviderError(Exception):
    """Raised when LLM provider configuration is invalid."""

    pass


def create_llm_adapter(
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> BaseLLMAdapter:
    """
    Create LLM adapter based on provider selection.

    Args:
        provider: Provider name ('claude' or 'openai'). If None, reads from LLM_PROVIDER env var.
        api_key: API key for provider. If None, reads from provider-specific env var.
        model: Model identifier. If None, uses provider default.

    Returns:
        Configured LLM adapter instance

    Raises:
        LLMProviderError: If provider is invalid or API key is missing
    """
    provider_config = {
        "claude": {
            "adapter_class": ClaudeAdapter,
            "env_var": "CLAUDE_API_KEY",
            "error_msg": "Claude API key not found. Set CLAUDE_API_KEY environment variable.",
        },
        "openai": {
            "adapter_class": OpenAIAdapter,
            "env_var": "OPENAI_API_KEY",
            "error_msg": "OpenAI API key not found. Set OPENAI_API_KEY environment variable.",
        },
    }

    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "claude").lower()

    if provider not in provider_config:
        valid_providers = ", ".join(f"'{p}'" for p in provider_config)
        raise LLMProviderError(f"Invalid LLM provider: '{provider}'. Must be {valid_providers}")

    config = provider_config[provider]

    if api_key is None:
        api_key = os.getenv(config["env_var"])

    if not api_key:
        raise LLMProviderError(config["error_msg"])

    adapter_class = config["adapter_class"]
    if model:
        return adapter_class(api_key=api_key, model=model)
    return adapter_class(api_key=api_key)
