"""Console progress formatting for execution events."""

from __future__ import annotations

import json

from agentic_engineer.execution.progress import format_progress_line
from agentic_engineer.llm.json_extract import describe_json_error
from agentic_engineer.models.execution import ExecutionEvent


def test_format_progress_line_includes_message_and_details() -> None:
    event = ExecutionEvent(
        event_type="task_start",
        message='Running t2 “API” via developer agent',
        task_id="t2",
        details={"agent": "developer", "retry_count": 1},
    )
    line = format_progress_line(event)
    assert "[task start]" in line
    assert "Running t2" in line
    assert "agent=developer" in line


def test_format_progress_line_omits_duplicate_task_id() -> None:
    event = ExecutionEvent(
        event_type="task_failed",
        message="Failed t2 “API” via developer agent: boom",
        task_id="t2",
    )
    line = format_progress_line(event)
    assert line.count("t2") == 1


def test_describe_json_error_explains_unterminated_string() -> None:
    try:
        json.loads('{"files": [{"path": "a.py", "content": "unterminated')
    except json.JSONDecodeError as exc:
        text = describe_json_error(exc)
    assert "invalid JSON" in text
    assert "Unterminated string" in text or "unterminated" in text.lower()
    # Must not inject "truncated"/"unclosed" — those poison failure classification.
    assert "truncated" not in text.lower()
    assert "unclosed" not in text.lower()
