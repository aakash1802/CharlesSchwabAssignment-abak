"""Explicit LLM / developer-agent failure categories and classified errors."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from agentic_engineer.llm.base import LLMError


class FailureCategory(str, Enum):
    """Failure categories derived from execution evidence (not task descriptions)."""

    TRANSIENT_PROVIDER = "transient_provider"
    RATE_LIMIT = "rate_limit"
    INVALID_STRUCTURED_OUTPUT = "invalid_structured_output"
    OUTPUT_TRUNCATED = "output_truncated"
    # Legacy alias kept for persisted tags / older code paths.
    TRUNCATED_RESPONSE = "truncated_response"
    SCHEMA_VALIDATION = "schema_validation"
    IMPLEMENTATION_ERROR = "implementation_error"
    # Legacy alias.
    IMPLEMENTATION = "implementation"
    TEST_FAILURE = "test_failure"
    DEPENDENCY_FAILURE = "dependency_failure"
    WORKSPACE_VIOLATION = "workspace_violation"
    # Legacy alias.
    WORKSPACE_SAFETY = "workspace_safety"
    INVALID_FILE_OPERATION = "invalid_file_operation"
    PERMISSION_FAILURE = "permission_failure"
    UNKNOWN = "unknown"


def normalize_category(category: FailureCategory) -> FailureCategory:
    """Collapse legacy aliases onto canonical categories."""
    if category in {
        FailureCategory.TRUNCATED_RESPONSE,
        FailureCategory.OUTPUT_TRUNCATED,
    }:
        return FailureCategory.OUTPUT_TRUNCATED
    if category in {
        FailureCategory.IMPLEMENTATION,
        FailureCategory.IMPLEMENTATION_ERROR,
    }:
        return FailureCategory.IMPLEMENTATION_ERROR
    if category in {
        FailureCategory.WORKSPACE_SAFETY,
        FailureCategory.WORKSPACE_VIOLATION,
    }:
        return FailureCategory.WORKSPACE_VIOLATION
    return category


# Categories that may auto-retry (subject to Python-owned caps).
RETRYABLE_CATEGORIES = frozenset(
    {
        FailureCategory.TRANSIENT_PROVIDER,
        FailureCategory.RATE_LIMIT,
        FailureCategory.INVALID_STRUCTURED_OUTPUT,
        FailureCategory.OUTPUT_TRUNCATED,
        FailureCategory.TRUNCATED_RESPONSE,
        FailureCategory.SCHEMA_VALIDATION,
        FailureCategory.IMPLEMENTATION_ERROR,
        FailureCategory.IMPLEMENTATION,
        FailureCategory.TEST_FAILURE,
        FailureCategory.DEPENDENCY_FAILURE,
        FailureCategory.UNKNOWN,
    }
)

# Prefer reducing generation scope rather than repeating the same oversized call.
REDUCE_SCOPE_CATEGORIES = frozenset(
    {
        FailureCategory.OUTPUT_TRUNCATED,
        FailureCategory.TRUNCATED_RESPONSE,
    }
)

# Never auto-retry — escalate for human intervention.
NON_RETRYABLE_CATEGORIES = frozenset(
    {
        FailureCategory.INVALID_FILE_OPERATION,
        FailureCategory.WORKSPACE_SAFETY,
        FailureCategory.WORKSPACE_VIOLATION,
        FailureCategory.PERMISSION_FAILURE,
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
            self.retryable = category not in NON_RETRYABLE_CATEGORIES
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
# Prefer explicit provider/parser truncation signals — avoid bare "truncated"
# so describe_json_error prose cannot poison classification.
_TRUNCATED_RE = re.compile(
    r"stop_reason=(?:max_tokens|length)|Model response truncated|"
    r"unterminated string|max_tokens|output_truncated",
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
_PERMISSION_RE = re.compile(
    r"permission denied|not authorized|access denied|EACCES|forbidden",
    re.I,
)
_DEPENDENCY_RE = re.compile(
    r"ModuleNotFoundError|No module named|cannot import|ImportError|"
    r"package not found|dependency .* unavailable|missing dependency",
    re.I,
)
# Case-insensitive test signals, plus case-sensitive pytest "FAILED <nodeid>"
# (IGNORECASE would also match "Command failed exit=N").
_TEST_RE = re.compile(
    r"(?i:\bpytest\b|test failed|assertionerror|tests? failed)|"
    r"FAILED\s+\S"
)


def classify_provider_exception(exc: BaseException) -> FailureCategory:
    """Map a raw provider/SDK exception to a failure category."""
    text = str(exc)
    if _RATE_LIMIT_RE.search(text):
        return FailureCategory.RATE_LIMIT
    if _TIMEOUT_RE.search(text) or _NETWORK_RE.search(text):
        return FailureCategory.TRANSIENT_PROVIDER
    if _TRUNCATED_RE.search(text):
        return FailureCategory.OUTPUT_TRUNCATED
    if _JSON_RE.search(text):
        return FailureCategory.INVALID_STRUCTURED_OUTPUT
    if _PERMISSION_RE.search(text):
        return FailureCategory.PERMISSION_FAILURE
    if _PATH_RE.search(text) or _WORKSPACE_RE.search(text):
        return FailureCategory.WORKSPACE_VIOLATION
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
    if _PERMISSION_RE.search(text):
        return FailureCategory.PERMISSION_FAILURE
    # Explicit truncation before generic JSON — "Unterminated string" is size-cut.
    # Generic "invalid JSON" without truncation signals stays structured-output.
    if _TRUNCATED_RE.search(text):
        return FailureCategory.OUTPUT_TRUNCATED
    if _PATH_RE.search(text) or _WORKSPACE_RE.search(text):
        return FailureCategory.WORKSPACE_VIOLATION
    if "Invalid file" in text or "file operation" in text.lower():
        return FailureCategory.INVALID_FILE_OPERATION
    if _JSON_RE.search(text):
        return FailureCategory.INVALID_STRUCTURED_OUTPUT
    if _SCHEMA_RE.search(text):
        return FailureCategory.SCHEMA_VALIDATION
    if _DEPENDENCY_RE.search(text):
        return FailureCategory.DEPENDENCY_FAILURE
    if _TEST_RE.search(text):
        return FailureCategory.TEST_FAILURE
    if _TIMEOUT_RE.search(text) or _NETWORK_RE.search(text):
        return FailureCategory.TRANSIENT_PROVIDER
    if "Forced failure" in text:
        return FailureCategory.UNKNOWN
    # Generic implementation signal when message mentions generated code/runtime.
    if re.search(r"implementation|generated code|TypeError|NameError|SyntaxError", text, re.I):
        return FailureCategory.IMPLEMENTATION_ERROR
    return FailureCategory.UNKNOWN


def format_classified_message(message: str, category: FailureCategory) -> str:
    """Attach a machine-readable category tag for persistence / analysis."""
    tag = f"[failure_category={category.value}]"
    if tag in message:
        return message
    return f"{tag} {message}"


def classify_command_evidence(
    *,
    exit_code: int,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
) -> FailureCategory:
    """Classify a failed approved command from captured evidence.

    Prefer dependency signals in stdout/stderr over generic exit-code text so
    missing packages are not mislabeled as test failures.
    """
    if timed_out:
        return FailureCategory.TRANSIENT_PROVIDER
    blob = f"{stdout or ''}\n{stderr or ''}".strip()
    if not blob:
        # Bare exit codes (e.g. "Command failed exit=4") are unknown — not tests.
        return FailureCategory.UNKNOWN
    if _DEPENDENCY_RE.search(blob):
        return FailureCategory.DEPENDENCY_FAILURE
    if _TEST_RE.search(blob):
        return FailureCategory.TEST_FAILURE
    # Fall back to message heuristics on the combined output only.
    return classify_from_message(blob)
