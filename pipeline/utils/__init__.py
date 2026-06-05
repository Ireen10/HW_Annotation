"""Pipeline-wide utilities (LLM client, shared helpers)."""

from .llm import LLMError, OpenAICompatibleClient

__all__ = ["LLMError", "OpenAICompatibleClient"]
