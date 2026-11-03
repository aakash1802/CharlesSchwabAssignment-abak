"""Parse provider responses into structured JSON / Pydantic models."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from agentic_engineer.llm.base import LLMError, LLMResponse
from agentic_engineer.llm.failures import ClassifiedLLMError, FailureCategory
from agentic_engineer.llm.json_extract import describe_json_error, extract_json_text

T = TypeVar("T", bound=BaseModel)


def assert_not_truncated(response: LLMResponse) -> None:
    """Raise before parse when the provider stopped due to token limit."""
    stop = (response.stop_reason or response.raw.get("stop_reason") or "").lower()
    if stop in {"max_tokens", "length"}:
        usage = response.usage or response.raw.get("usage") or {}
        raise ClassifiedLLMError(
            f"Model response truncated (stop_reason={stop})",
            category=FailureCategory.TRUNCATED_RESPONSE,
            details={
                "stop_reason": stop,
                "usage": usage,
                "response_type": response.response_type,
            },
        )


def extract_structured_dict(response: LLMResponse) -> dict[str, Any]:
    """
    Obtain a JSON object from an LLMResponse.

    Prefers provider-populated `structured`, then text / fenced JSON extraction.
    """
    assert_not_truncated(response)
    if response.response_type == "empty" or (
        not (response.text or "").strip() and response.structured is None
    ):
        raise ClassifiedLLMError(
            "Empty model response",
            category=FailureCategory.INVALID_STRUCTURED_OUTPUT,
            details={"response_type": response.response_type},
        )

    if isinstance(response.structured, dict):
        return response.structured

    try:
        text = extract_json_text(response.text)
        data = json.loads(text)
    except LLMError as exc:
        raise ClassifiedLLMError(
            str(exc),
            category=FailureCategory.INVALID_STRUCTURED_OUTPUT,
            details={"response_type": response.response_type},
        ) from exc
    except json.JSONDecodeError as exc:
        raise ClassifiedLLMError(
            describe_json_error(exc),
            category=FailureCategory.INVALID_STRUCTURED_OUTPUT,
            details={
                "response_type": response.response_type,
                "lineno": exc.lineno,
                "colno": exc.colno,
            },
        ) from exc

    if not isinstance(data, dict):
        raise ClassifiedLLMError(
            "Structured output must be a JSON object",
            category=FailureCategory.SCHEMA_VALIDATION,
        )
    return data


def parse_structured_model(response: LLMResponse, model_type: type[T]) -> T:
    """Parse and validate a response against a Pydantic model."""
    data = extract_structured_dict(response)
    try:
        return model_type.model_validate(data)
    except ValidationError as exc:
        raise ClassifiedLLMError(
            f"Schema validation failed: {exc.error_count()} error(s)",
            category=FailureCategory.SCHEMA_VALIDATION,
            details={"errors": exc.errors()},
        ) from exc
