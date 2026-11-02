"""Deterministic mock provider for tests and offline runs."""

from __future__ import annotations

from agentic_engineer.llm.base import LLMError, LLMRequest, LLMResponse


class MockProvider:
    """
    Returns scripted responses in order, or a single default string.

    Usage in tests:
        MockProvider(responses=["first", "second"])
        MockProvider(default_text='{"ok": true}')
    """

    def __init__(
        self,
        *,
        responses: list[str] | None = None,
        default_text: str = '{"status": "mock"}',
        model: str = "mock-model",
    ) -> None:
        self._queue = list(responses or [])
        self._default_text = default_text
        self._model = model
        self.calls: list[LLMRequest] = []

    @property
    def has_queued_responses(self) -> bool:
        return bool(self._queue)

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if not request.prompt.strip():
            raise LLMError("Empty prompt")
        if self._queue:
            text = self._queue.pop(0)
        else:
            text = self._default_text
        return LLMResponse(
            text=text,
            model=request.model or self._model,
            raw={"provider": "mock"},
        )
