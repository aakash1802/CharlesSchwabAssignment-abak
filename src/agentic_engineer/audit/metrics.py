"""Derive metrics.json only from recorded audit events (never fabricate)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentic_engineer.models.common import utc_now
from agentic_engineer.models.execution import ExecutionEvent
from agentic_engineer.persistence.json_store import JsonStore


class MetricsSnapshot(BaseModel):
    """Metrics computed from audit events; gaps called out explicitly."""

    schema_version: int = 1
    workflow_id: str
    event_count: int = 0
    task_starts: int = 0
    task_finishes: int = 0
    task_failures: int = 0
    retries: int = 0
    commands_proposed: int = 0
    commands_approved: int = 0
    commands_rejected: int = 0
    commands_executed: int = 0
    replans: int = 0
    safe_stops: int = 0
    completed: bool = False
    insufficient_data: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    computed_at: str = Field(default_factory=lambda: utc_now().isoformat())


def derive_metrics(workflow_id: str, events: list[ExecutionEvent]) -> MetricsSnapshot:
    counts: dict[str, int] = {
        "task_start": 0,
        "task_finish": 0,
        "task_failed": 0,
        "retry": 0,
        "command_proposed": 0,
        "command_approved": 0,
        "command_rejected": 0,
        "command_executed": 0,
        "replan": 0,
        "safe_stop": 0,
        "completed": 0,
    }
    for event in events:
        key = event.event_type
        if key in counts:
            counts[key] += 1

    insufficient: list[str] = []
    notes: list[str] = []
    if not events:
        insufficient.append("No audit events recorded; rates and latencies unavailable")
    else:
        # Latencies / MTTR require paired timestamps we do not yet store as spans.
        insufficient.append(
            "e2e latency, approval wait time, and MTTR not computed "
            "(no duration spans in event stream)"
        )

    return MetricsSnapshot(
        workflow_id=workflow_id,
        event_count=len(events),
        task_starts=counts["task_start"],
        task_finishes=counts["task_finish"],
        task_failures=counts["task_failed"],
        retries=counts["retry"],
        commands_proposed=counts["command_proposed"],
        commands_approved=counts["command_approved"],
        commands_rejected=counts["command_rejected"],
        commands_executed=counts["command_executed"],
        replans=counts["replan"],
        safe_stops=counts["safe_stop"],
        completed=counts["completed"] > 0,
        insufficient_data=insufficient,
        notes=notes,
    )


def write_metrics(workflow_dir: Path, snapshot: MetricsSnapshot) -> Path:
    store = JsonStore(workflow_dir)
    store.write_json("metrics.json", snapshot.model_dump(mode="json"))
    return workflow_dir / "metrics.json"


def metrics_dict(snapshot: MetricsSnapshot) -> dict[str, Any]:
    return snapshot.model_dump(mode="json")
