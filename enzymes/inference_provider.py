"""Backward-compatible forwarding shim for enzymes.inference_provider.

Delegates down to soma_core.inference_provider.
"""
from soma_core.inference_provider import (
    AnthropicProvider,
    GeminiProvider,
    InferenceProvider,
    InferenceUnavailableError,
    OpenAIProvider,
    PromptOnlyProvider,
    read_config_key,
    resolve_key,
    resolve_provider,
)

__all__ = [
    "AnthropicProvider",
    "GeminiProvider",
    "InferenceProvider",
    "InferenceUnavailableError",
    "OpenAIProvider",
    "PromptOnlyProvider",
    "read_config_key",
    "resolve_key",
    "resolve_provider",
]
