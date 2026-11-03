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
    same_operation_retries: int = 0
    corrected_retries: int = 0
    scope_reductions: int = 0
    escalations: int = 0
    recovery_decisions: int = 0
    recovery_successes: int = 0
    repeated_failure_signals: int = 0
    recovery_success_rate: float | None = None
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
        "recovery_decision": 0,
        "scope_reduced": 0,
        "escalation": 0,
    }
    same_retries = 0
    corrected_retries = 0
    repeated_signals = 0
    for event in events:
        key = event.event_type
        if key in counts:
            counts[key] += 1
        if key == "recovery_decision":
            strategy = str((event.details or {}).get("strategy") or "")
            if strategy == "retry_same":
                same_retries += 1
            elif strategy == "retry_corrected":
                corrected_retries += 1
            evidence = event.details.get("evidence") if event.details else None
            if isinstance(evidence, list) and any(
                "repeated ineffective" in str(item).lower()
                or "escalated strategy after repeated" in str(item).lower()
                for item in evidence
            ):
                repeated_signals += 1

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

    recovery_decisions = counts["recovery_decision"]
    # Success approximation: task finishes after a recovery decision in the stream.
    # Only report a rate when both sides are present; never fabricate.
    recovery_successes = 0
    recovery_success_rate: float | None = None
    if recovery_decisions and counts["task_finish"]:
        # Conservative: count finishes that follow any recovery as successes when
        # the workflow also recorded retries/scope reductions without escalation.
        recovery_successes = max(
            0, counts["retry"] + counts["scope_reduced"] - counts["escalation"]
        )
        # Do not invent a rate if we cannot attribute successes cleanly.
        if recovery_successes > recovery_decisions:
            recovery_successes = recovery_decisions
        if recovery_decisions > 0 and (
            counts["retry"] or counts["scope_reduced"] or counts["replan"]
        ):
            notes.append(
                "recovery_success_rate uses retry/scope events minus escalations; "
                "not a precise per-attempt attribution"
            )
            recovery_success_rate = round(
                recovery_successes / recovery_decisions, 4
            )
        else:
            insufficient.append(
                "recovery success rate not computed (insufficient attribution data)"
            )
    elif recovery_decisions:
        insufficient.append(
            "recovery success rate not computed (no subsequent task finishes)"
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
        same_operation_retries=same_retries,
        corrected_retries=corrected_retries,
        scope_reductions=counts["scope_reduced"],
        escalations=counts["escalation"],
        recovery_decisions=recovery_decisions,
        recovery_successes=recovery_successes,
        repeated_failure_signals=repeated_signals,
        recovery_success_rate=recovery_success_rate,
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
