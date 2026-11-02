"""Provider protocol and shared request/response types."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class LLMError(Exception):
    """Provider or parsing failure."""


class LLMRequest(BaseModel):
    prompt: str
    system: str | None = None
    model: str | None = None
    timeout_seconds: float | None = None
    response_schema_name: str | None = Field(
        default=None,
        description="Optional logical schema name for structured outputs",
    )


class LLMResponse(BaseModel):
    text: str
    model: str
    raw: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """Replaceable LLM backend (Phase 2: MockProvider | AnthropicProvider)."""

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a completion; raise LLMError on failure."""
        ...
