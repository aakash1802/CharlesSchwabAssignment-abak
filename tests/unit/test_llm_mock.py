"""Mock LLM provider tests."""

from __future__ import annotations

import pytest

from agentic_engineer.llm import LLMError, LLMRequest, MockProvider


def test_mock_queue_and_default() -> None:
    provider = MockProvider(responses=["one", "two"], default_text="fallback")
    assert provider.complete(LLMRequest(prompt="a")).text == "one"
    assert provider.complete(LLMRequest(prompt="b")).text == "two"
    assert provider.complete(LLMRequest(prompt="c")).text == "fallback"
    assert len(provider.calls) == 3


def test_mock_rejects_empty_prompt() -> None:
    provider = MockProvider()
    with pytest.raises(LLMError):
        provider.complete(LLMRequest(prompt="   "))
