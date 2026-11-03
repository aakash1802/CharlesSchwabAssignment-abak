"""Explicit LLM / developer-agent failure categories and classified errors."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from agentic_engineer.llm.base import LLMError


class FailureCategory(str, Enum):
    TRANSIENT_PROVIDER = "transient_provider"
    RATE_LIMIT = "rate_limit"
    INVALID_STRUCTURED_OUTPUT = "invalid_structured_output"
    TRUNCATED_RESPONSE = "truncated_response"
    SCHEMA_VALIDATION = "schema_validation"
    INVALID_FILE_OPERATION = "invalid_file_operation"
    WORKSPACE_SAFETY = "workspace_safety"
    IMPLEMENTATION = "implementation"


# Categories that may auto-retry (subject to Python-owned caps).
RETRYABLE_CATEGORIES = frozenset(
    {
        FailureCategory.TRANSIENT_PROVIDER,
        FailureCategory.RATE_LIMIT,
        FailureCategory.INVALID_STRUCTURED_OUTPUT,
        FailureCategory.TRUNCATED_RESPONSE,
        FailureCategory.SCHEMA_VALIDATION,
        FailureCategory.IMPLEMENTATION,
    }
)

# Prefer reducing generation scope rather than repeating the same oversized call.
REDUCE_SCOPE_CATEGORIES = frozenset(
    {
        FailureCategory.TRUNCATED_RESPONSE,
    }
)

# Never auto-retry — safe-stop / human intervention.
NON_RETRYABLE_CATEGORIES = frozenset(
    {
        FailureCategory.INVALID_FILE_OPERATION,
        FailureCategory.WORKSPACE_SAFETY,
    }
)


class ClassifiedLLMError(LLMError):
    """LLM/agent failure with an explicit category for retry policy."""

    def __init__(
        self,
        message: str,
        *,
        category: FailureCategory,
        details: dict[str, Any] | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.details = details or {}
        if retryable is None:
            self.retryable = category in RETRYABLE_CATEGORIES
        else:
            self.retryable = retryable

    def with_prefix(self, prefix: str) -> ClassifiedLLMError:
        return ClassifiedLLMError(
            f"{prefix}: {self}",
            category=self.category,
            details=dict(self.details),
            retryable=self.retryable,
        )


_RATE_LIMIT_RE = re.compile(r"rate.?limit|429|too many requests", re.I)
_TIMEOUT_RE = re.compile(r"timeout|timed out|deadline exceeded", re.I)
_NETWORK_RE = re.compile(
    r"connection|network|temporarily unavailable|503|502|504|overloaded",
    re.I,
)
_TRUNCATED_RE = re.compile(
    r"truncated|max_tokens|unterminated string|unclosed",
    re.I,
)
_JSON_RE = re.compile(
    r"invalid JSON|Expecting |JSONDecodeError|did not contain JSON|Empty model",
    re.I,
)
_SCHEMA_RE = re.compile(r"schema|validation error|pydantic|Payload must", re.I)
_PATH_RE = re.compile(
    r"Invalid path|Path escapes|not allowed|\.agentic/|symlink",
    re.I,
)
_WORKSPACE_RE = re.compile(r"workspace|isolation|escapes workspace", re.I)


def classify_provider_exception(exc: BaseException) -> FailureCategory:
    """Map a raw provider/SDK exception to a failure category."""
    text = str(exc)
    if _RATE_LIMIT_RE.search(text):
        return FailureCategory.RATE_LIMIT
    if _TIMEOUT_RE.search(text) or _NETWORK_RE.search(text):
        return FailureCategory.TRANSIENT_PROVIDER
    if _TRUNCATED_RE.search(text):
        return FailureCategory.TRUNCATED_RESPONSE
    if _JSON_RE.search(text):
        return FailureCategory.INVALID_STRUCTURED_OUTPUT
    if _PATH_RE.search(text) or _WORKSPACE_RE.search(text):
        return FailureCategory.WORKSPACE_SAFETY
    if _SCHEMA_RE.search(text):
        return FailureCategory.SCHEMA_VALIDATION
    return FailureCategory.TRANSIENT_PROVIDER


def classify_from_message(message: str) -> FailureCategory:
    """Best-effort category from an error string (e.g. persisted task.error)."""
    if isinstance(message, ClassifiedLLMError):  # pragma: no cover
        return message.category
    text = message or ""
    # Prefer explicit tagged category if present.
    tagged = re.search(r"\[failure_category=([a-z_]+)\]", text)
    if tagged:
        try:
            return FailureCategory(tagged.group(1))
        except ValueError:
            pass
    if _RATE_LIMIT_RE.search(text):
        return FailureCategory.RATE_LIMIT
    if _TRUNCATED_RE.search(text):
        return FailureCategory.TRUNCATED_RESPONSE
    if _PATH_RE.search(text) or _WORKSPACE_RE.search(text):
        return FailureCategory.WORKSPACE_SAFETY
    if "Invalid file" in text or "file operation" in text.lower():
        return FailureCategory.INVALID_FILE_OPERATION
    if _JSON_RE.search(text):
        return FailureCategory.INVALID_STRUCTURED_OUTPUT
    if _SCHEMA_RE.search(text):
        return FailureCategory.SCHEMA_VALIDATION
    if _TIMEOUT_RE.search(text) or _NETWORK_RE.search(text):
        return FailureCategory.TRANSIENT_PROVIDER
    return FailureCategory.IMPLEMENTATION


def format_classified_message(message: str, category: FailureCategory) -> str:
    """Attach a machine-readable category tag for persistence / analysis."""
    tag = f"[failure_category={category.value}]"
    if tag in message:
        return message
    return f"{tag} {message}"
