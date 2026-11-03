"""Deterministic mock provider for tests and offline runs."""

from __future__ import annotations

from typing import Any

from agentic_engineer.llm.base import LLMError, LLMRequest, LLMResponse
from agentic_engineer.llm.failures import ClassifiedLLMError


class MockProvider:
    """
    Returns scripted responses in order, or a single default string.

    Usage in tests:
        MockProvider(responses=["first", "second"])
        MockProvider(default_text='{"ok": true}')
        MockProvider(responses=[LLMResponse(...), ClassifiedLLMError(...)])
    """

    def __init__(
        self,
        *,
        responses: list[Any] | None = None,
        default_text: str = '{"status": "mock"}',
        model: str = "mock-model",
    ) -> None:
        self._scripted = responses is not None
        self._queue = list(responses or [])
        self._default_text = default_text
        self._model = model
        self.calls: list[LLMRequest] = []

    @property
    def has_queued_responses(self) -> bool:
        # Scripted providers stay on the LLM path even after the queue drains
        # so agents do not silently fall back to stub filesystem writes.
        return self._scripted or bool(self._queue)

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if not request.prompt.strip():
            raise LLMError("Empty prompt")
        if self._queue:
            item = self._queue.pop(0)
        else:
            item = self._default_text

        if isinstance(item, ClassifiedLLMError):
            raise item
        if isinstance(item, Exception):
            raise item
        if isinstance(item, LLMResponse):
            return item
        if isinstance(item, dict):
            return LLMResponse(
                text=str(item.get("text") or ""),
                model=str(item.get("model") or request.model or self._model),
                raw=dict(item.get("raw") or {"provider": "mock"}),
                stop_reason=item.get("stop_reason"),
                usage=dict(item.get("usage") or {}),
                response_type=str(item.get("response_type") or "text"),
                structured=item.get("structured"),
            )
        return LLMResponse(
            text=str(item),
            model=request.model or self._model,
            raw={"provider": "mock"},
            response_type="text",
        )
