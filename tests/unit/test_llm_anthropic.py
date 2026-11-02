"""Anthropic provider unit tests (SDK mocked — no live API calls)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agentic_engineer.config.settings import Settings, clear_settings_cache
from agentic_engineer.llm import LLMError, LLMRequest, build_provider
from agentic_engineer.llm.anthropic_provider import AnthropicProvider
from agentic_engineer.llm.json_extract import extract_json_text
from agentic_engineer.llm.mock import MockProvider


def test_extract_json_from_fence() -> None:
    raw = 'Sure.\n```json\n{"ok": true}\n```\n'
    assert extract_json_text(raw) == '{"ok": true}'


def test_anthropic_complete_with_injected_client() -> None:
    message = SimpleNamespace(
        id="msg_1",
        model="claude-sonnet-5-5",
        stop_reason="end_turn",
        content=[SimpleNamespace(text='{"summary": "x", "needs_clarification": false}')],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: message))
    provider = AnthropicProvider(
        api_key="test-key",
        model="claude-sonnet-5-5",
        client=client,
    )
    response = provider.complete(
        LLMRequest(
            prompt="Analyze this",
            system="Return JSON",
            response_schema_name="RequirementAnalysis",
        )
    )
    assert '"summary": "x"' in response.text
    assert response.model == "claude-sonnet-5-5"
    assert response.raw["provider"] == "anthropic"


def test_anthropic_requires_api_key() -> None:
    with pytest.raises(LLMError, match="API key"):
        AnthropicProvider(api_key="")


def test_factory_mock_default() -> None:
    clear_settings_cache()
    provider = build_provider(Settings(llm_provider="mock"))
    assert isinstance(provider, MockProvider)


def test_factory_anthropic_missing_key() -> None:
    clear_settings_cache()
    with pytest.raises(LLMError, match="API key"):
        build_provider(Settings(llm_provider="anthropic", llm_api_key=None))


def test_factory_anthropic_builds(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings(
        llm_provider="anthropic",
        llm_api_key="sk-ant-test",
        llm_model="claude-sonnet-5-5",
    )
    # Avoid importing real SDK network client: inject via monkeypatch on class init path
    created: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            created.update(kwargs)

        def complete(self, request):  # pragma: no cover
            raise NotImplementedError

    monkeypatch.setattr(
        "agentic_engineer.llm.anthropic_provider.AnthropicProvider",
        FakeProvider,
    )
    provider = build_provider(settings)
    assert isinstance(provider, FakeProvider)
    assert created["api_key"] == "sk-ant-test"
    assert created["model"] == "claude-sonnet-5-5"


def test_resolved_model_default_for_anthropic() -> None:
    settings = Settings(llm_provider="anthropic", llm_model="mock-model")
    assert settings.resolved_llm_model() == "claude-sonnet-5-5"
