"""Anthropic (Claude) LLM provider."""

from __future__ import annotations

from typing import Any

from agentic_engineer.llm.base import LLMError, LLMRequest, LLMResponse
from agentic_engineer.llm.json_extract import extract_json_text


class AnthropicProvider:
    """
    Calls Anthropic Messages API and returns assistant text.

    When the request asks for a structured schema, the returned `text` is
    normalized to a JSON object/array string suitable for Pydantic parsing.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-4-5",
        timeout_seconds: float = 60.0,
        max_tokens: int = 4096,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise LLMError(
                "Anthropic API key missing. Set AGENTIC_LLM_API_KEY or ANTHROPIC_API_KEY."
            )
        self._model = model
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens
        if client is not None:
            self._client = client
        else:
            try:
                from anthropic import Anthropic
            except ImportError as exc:  # pragma: no cover
                raise LLMError(
                    "The 'anthropic' package is required for AGENTIC_LLM_PROVIDER=anthropic. "
                    'Install with: pip install -e ".[anthropic]" or pip install anthropic'
                ) from exc
            self._client = Anthropic(api_key=api_key, timeout=timeout_seconds)

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not request.prompt.strip():
            raise LLMError("Empty prompt")

        model = request.model or self._model
        system = request.system or "You are a helpful assistant."
        if request.response_schema_name:
            system = (
                f"{system}\n\n"
                "Respond with a single JSON object only. "
                "Do not include markdown commentary outside JSON."
            )

        timeout = request.timeout_seconds or self._timeout
        try:
            message = self._client.messages.create(
                model=model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": request.prompt}],
                timeout=timeout,
            )
        except LLMError:
            raise
        except Exception as exc:  # SDK / network errors
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        raw_text = _content_to_text(message)
        text = (
            extract_json_text(raw_text)
            if request.response_schema_name
            else raw_text
        )
        return LLMResponse(
            text=text,
            model=getattr(message, "model", None) or model,
            raw={
                "provider": "anthropic",
                "id": getattr(message, "id", None),
                "stop_reason": getattr(message, "stop_reason", None),
                "usage": _usage_dict(message),
            },
        )


def _content_to_text(message: Any) -> str:
    blocks = getattr(message, "content", None) or []
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
        elif isinstance(block, dict) and block.get("text"):
            parts.append(str(block["text"]))
    if not parts:
        raise LLMError("Anthropic response contained no text content")
    return "\n".join(parts).strip()


def _usage_dict(message: Any) -> dict[str, Any]:
    usage = getattr(message, "usage", None)
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }
