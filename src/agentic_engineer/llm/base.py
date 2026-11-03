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
    max_tokens: int | None = Field(
        default=None,
        description="Optional per-request max output tokens override",
    )
    response_schema_name: str | None = Field(
        default=None,
        description="Optional logical schema name for structured outputs",
    )
    response_json_schema: dict[str, Any] | None = Field(
        default=None,
        description="Optional JSON Schema for provider-constrained structured output",
    )


class LLMResponse(BaseModel):
    text: str
    model: str
    raw: dict[str, Any] = Field(default_factory=dict)
    stop_reason: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    response_type: str = Field(
        default="text",
        description="Content shape: text | tool_use | structured_json | empty",
    )
    structured: dict[str, Any] | None = Field(
        default=None,
        description="Provider-parsed structured payload when available",
    )


@runtime_checkable
class LLMProvider(Protocol):
    """Replaceable LLM backend (Phase 2: MockProvider | AnthropicProvider)."""

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a completion; raise LLMError on failure."""
        ...
