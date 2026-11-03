"""Typed LangGraph state for Phase 4 execution."""

from __future__ import annotations

from typing import Any, TypedDict


class ExecutionGraphState(TypedDict, total=False):
    workflow_id: str
    thread_id: str
    plan_id: str
    tasks: list[dict[str, Any]]
    design_note: str
    inspect_summary: dict[str, Any]
    current_cohort: list[str]
    cohort_queue: list[str]
    cohort_index: int
    current_task_id: str | None
    pending_command: dict[str, Any] | None
    pending_destructive: dict[str, Any] | None
    test_results: list[dict[str, Any]]
    errors: list[str]
    stop_reason: str | None
    phase: str
    next_phase_index: int
    last_failure: dict[str, Any] | None
    failure_recommendation: str | None
    recovery_strategy: str | None
    recovery_decision: dict[str, Any] | None
    recovery_history: list[dict[str, Any]]
    human_intervention: dict[str, Any] | None
    force_fail_task_ids: list[str]
    force_destructive_task_ids: list[str]
    force_replan_task_ids: list[str]
    plan_patch: dict[str, Any] | None
    awaiting_plan_reapproval: bool
    awaiting_release: bool
    completed: bool
    safe_stopped: bool
    written_paths: list[str]
