"""Human-readable execution progress lines for the CLI console."""

from __future__ import annotations

from typing import Callable

from agentic_engineer.models.execution import ExecutionEvent

ProgressSink = Callable[[ExecutionEvent], None]

# Event types that should stand out as failures / stops.
_ERROR_TYPES = frozenset(
    {
        "task_failed",
        "safe_stop",
        "command_rejected",
        "destructive_rejected",
    }
)
_WARN_TYPES = frozenset(
    {
        "retry",
        "fail_analyzed",
        "replan",
        "command_executed",
    }
)


def format_progress_line(event: ExecutionEvent) -> str:
    """One-line console summary for an execution audit event."""
    label = event.event_type.replace("_", " ")
    parts: list[str] = [f"[{label}]"]
    if event.task_id and event.task_id not in (event.message or ""):
        parts.append(f"task={event.task_id}")
    if event.message:
        parts.append(event.message)
    details = event.details or {}
    # Surface a few high-signal detail keys without dumping the whole dict.
    for key in ("recommendation", "exit_code", "passed", "cohort_index", "agent"):
        if key in details and details[key] is not None:
            parts.append(f"{key}={details[key]}")
    return " ".join(parts)


def echo_progress(event: ExecutionEvent) -> None:
    """Print a colored progress line to the CLI (stdout)."""
    import typer

    line = format_progress_line(event)
    if event.event_type in _ERROR_TYPES:
        typer.secho(line, fg=typer.colors.RED, err=False)
    elif event.event_type in _WARN_TYPES and (
        event.event_type != "command_executed"
        or event.details.get("passed") is False
    ):
        typer.secho(line, fg=typer.colors.YELLOW, err=False)
    elif event.event_type in {"task_finish", "completed", "docs_written"}:
        typer.secho(line, fg=typer.colors.GREEN, err=False)
    else:
        typer.secho(line, fg=typer.colors.CYAN, err=False)
