"""Anthropic (Claude) LLM provider."""

from __future__ import annotations

import json
from typing import Any

from agentic_engineer.llm.base import LLMError, LLMRequest, LLMResponse
from agentic_engineer.llm.failures import (
    ClassifiedLLMError,
    FailureCategory,
    classify_provider_exception,
)
from agentic_engineer.llm.json_extract import extract_json_text


class AnthropicProvider:
    """
    Calls Anthropic Messages API and returns assistant text / structured data.

    When `response_json_schema` (or a schema name) is set, prefers provider
    constrained JSON via `output_config.format`. Falls back to tool-use with an
    input schema, then to prompted JSON text extraction.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-5-5",
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
        wants_structured = bool(
            request.response_json_schema or request.response_schema_name
        )
        if wants_structured:
            system = (
                f"{system}\n\n"
                "Return a single JSON object that matches the required schema. "
                "Do not include markdown commentary outside JSON."
            )

        timeout = request.timeout_seconds or self._timeout
        max_tokens = request.max_tokens or self._max_tokens
        schema = request.response_json_schema

        try:
            message = self._create_message(
                model=model,
                system=system,
                prompt=request.prompt,
                max_tokens=max_tokens,
                timeout=timeout,
                schema=schema,
                schema_name=request.response_schema_name or "StructuredOutput",
            )
        except ClassifiedLLMError:
            raise
        except LLMError:
            raise
        except Exception as exc:  # SDK / network errors
            category = classify_provider_exception(exc)
            raise ClassifiedLLMError(
                f"Anthropic request failed: {exc}",
                category=category,
            ) from exc

        stop_reason = getattr(message, "stop_reason", None)
        usage = _usage_dict(message)
        extracted = _extract_content(message)
        text = extracted["text"]
        structured = extracted["structured"]
        response_type = extracted["response_type"]

        if stop_reason in {"max_tokens", "length"}:
            # Surface truncation explicitly; callers must not re-parse as JSON.
            return LLMResponse(
                text=text,
                model=getattr(message, "model", None) or model,
                stop_reason=str(stop_reason),
                usage=usage,
                response_type=response_type or "truncated",
                structured=structured,
                raw={
                    "provider": "anthropic",
                    "id": getattr(message, "id", None),
                    "stop_reason": stop_reason,
                    "usage": usage,
                    "truncated": True,
                },
            )

        if wants_structured and structured is None and text:
            try:
                structured = json.loads(extract_json_text(text))
                if isinstance(structured, dict):
                    text = json.dumps(structured)
                    response_type = response_type or "structured_json"
            except (LLMError, json.JSONDecodeError, TypeError):
                # Leave raw text; structured_parse will classify.
                pass
        elif wants_structured and structured is not None:
            text = json.dumps(structured)
            response_type = "structured_json"

        if response_type == "empty" or (not text.strip() and structured is None):
            raise ClassifiedLLMError(
                "Anthropic response contained no usable content",
                category=FailureCategory.INVALID_STRUCTURED_OUTPUT,
                details={"stop_reason": stop_reason, "response_type": response_type},
            )

        return LLMResponse(
            text=text,
            model=getattr(message, "model", None) or model,
            stop_reason=str(stop_reason) if stop_reason else None,
            usage=usage,
            response_type=response_type or "text",
            structured=structured if isinstance(structured, dict) else None,
            raw={
                "provider": "anthropic",
                "id": getattr(message, "id", None),
                "stop_reason": stop_reason,
                "usage": usage,
            },
        )

    def _create_message(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        max_tokens: int,
        timeout: float,
        schema: dict[str, Any] | None,
        schema_name: str,
    ) -> Any:
        base_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "timeout": timeout,
        }
        if schema:
            # Prefer JSON structured outputs when the SDK/API supports them.
            try:
                return self._client.messages.create(
                    **base_kwargs,
                    output_config={
                        "format": {
                            "type": "json_schema",
                            "schema": schema,
                        }
                    },
                )
            except TypeError:
                # Older SDK without output_config — try tool use.
                pass
            except Exception as exc:
                # Some models/accounts may reject output_config; fall through.
                if "output_config" not in str(exc).lower() and "json_schema" not in str(
                    exc
                ).lower():
                    # Unexpected failure — still try tool fallback before raising.
                    pass

            tool_name = _safe_tool_name(schema_name)
            tool_prompt = (
                f"{prompt}\n\n"
                f"You must call the `{tool_name}` tool with the complete result."
            )
            tool_kwargs = {
                **base_kwargs,
                "messages": [{"role": "user", "content": tool_prompt}],
                "tools": [
                    {
                        "name": tool_name,
                        "description": f"Submit structured result for {schema_name}",
                        "input_schema": schema,
                    }
                ],
                # Sonnet 5.5 rejects forced tool_choice; use auto + prompt instruction.
                "tool_choice": {"type": "auto"},
            }
            # Enable strict schema when supported.
            try:
                tool_kwargs["tools"][0]["strict"] = True
                return self._client.messages.create(**tool_kwargs)
            except Exception:
                tool_kwargs["tools"][0].pop("strict", None)
                try:
                    return self._client.messages.create(**tool_kwargs)
                except Exception:
                    # Last resort: plain prompted JSON (no provider constraint).
                    pass

        return self._client.messages.create(**base_kwargs)


def _safe_tool_name(schema_name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in schema_name)
    return (cleaned or "submit_result")[:64]


def _extract_content(message: Any) -> dict[str, Any]:
    blocks = getattr(message, "content", None) or []
    text_parts: list[str] = []
    structured: dict[str, Any] | None = None
    saw_tool = False
    saw_unexpected = False

    for block in blocks:
        btype = getattr(block, "type", None)
        if btype is None and isinstance(block, dict):
            btype = block.get("type")

        if btype in {None, "text"}:
            text = getattr(block, "text", None)
            if text is None and isinstance(block, dict):
                text = block.get("text")
            if text:
                text_parts.append(str(text))
            continue

        if btype == "tool_use":
            saw_tool = True
            tool_input = getattr(block, "input", None)
            if tool_input is None and isinstance(block, dict):
                tool_input = block.get("input")
            if isinstance(tool_input, dict):
                structured = tool_input
            elif isinstance(tool_input, str):
                try:
                    parsed = json.loads(tool_input)
                    if isinstance(parsed, dict):
                        structured = parsed
                except json.JSONDecodeError:
                    text_parts.append(tool_input)
            continue

        # Ignore thinking / other blocks; flag truly unexpected typed content.
        if btype not in {"thinking", "redacted_thinking", "server_tool_use"}:
            saw_unexpected = True

    text = "\n".join(text_parts).strip()
    if structured is not None:
        response_type = "tool_use" if saw_tool else "structured_json"
    elif text:
        response_type = "text"
    elif saw_unexpected:
        response_type = "unexpected_block"
    else:
        response_type = "empty"

    return {
        "text": text,
        "structured": structured,
        "response_type": response_type,
    }


def _usage_dict(message: Any) -> dict[str, Any]:
    usage = getattr(message, "usage", None)
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }
