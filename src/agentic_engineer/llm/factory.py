"""Build the configured LLM provider."""

from __future__ import annotations

from agentic_engineer.config.settings import Settings, get_settings
from agentic_engineer.llm.base import LLMError, LLMProvider
from agentic_engineer.llm.mock import MockProvider


def build_provider(settings: Settings | None = None) -> LLMProvider:
    """
    Construct the process LLM backend.

    Phase 2 providers:
    - mock (default; CI / offline)
    - anthropic (live Claude via API key)
    """
    cfg = settings or get_settings()
    name = cfg.llm_provider

    if name == "mock":
        return MockProvider(model=cfg.resolved_llm_model())

    if name == "anthropic":
        from agentic_engineer.llm.anthropic_provider import AnthropicProvider

        key = cfg.resolved_llm_api_key()
        if not key:
            raise LLMError(
                "Anthropic selected but no API key found. "
                "Set AGENTIC_LLM_API_KEY or ANTHROPIC_API_KEY."
            )
        return AnthropicProvider(
            api_key=key,
            model=cfg.resolved_llm_model(),
            timeout_seconds=cfg.llm_timeout_seconds,
            max_tokens=cfg.llm_max_tokens,
        )

    raise ValueError(
        f"Unsupported LLM provider {name!r}. "
        "Supported: mock, anthropic. Set AGENTIC_LLM_PROVIDER accordingly."
    )
