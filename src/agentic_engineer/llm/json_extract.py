"""Extract a JSON object string from an LLM reply (plain or fenced)."""

from __future__ import annotations

import json
import re

from agentic_engineer.llm.base import LLMError

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def describe_json_error(exc: BaseException) -> str:
    """Human-readable reason when model output fails JSON parsing.

    Avoid words like "truncated"/"unclosed" here — recovery classification
    matches those and would mis-label ordinary JSON errors as OUTPUT_TRUNCATED.
    """
    if isinstance(exc, json.JSONDecodeError):
        return (
            f"LLM returned invalid JSON ({exc.msg} at line {exc.lineno} "
            f"column {exc.colno})."
        )
    return str(exc)


def extract_json_text(text: str) -> str:
    """
    Return the JSON object/array substring from model output.

    Accepts raw JSON or a Markdown fenced ```json block.
    """
    cleaned = text.strip()
    if not cleaned:
        raise LLMError("Empty model response")

    fenced = _FENCE.search(cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()

    if cleaned.startswith("{") or cleaned.startswith("["):
        return cleaned

    start_obj = cleaned.find("{")
    start_arr = cleaned.find("[")
    starts = [i for i in (start_obj, start_arr) if i >= 0]
    if not starts:
        raise LLMError("Model response did not contain JSON")
    start = min(starts)
    end_obj = cleaned.rfind("}")
    end_arr = cleaned.rfind("]")
    end = max(end_obj, end_arr)
    if end <= start:
        raise LLMError("Model response JSON was truncated or malformed")
    return cleaned[start : end + 1]
