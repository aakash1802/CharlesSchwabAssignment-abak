"""Conditional edge helpers for the execution graph."""

from __future__ import annotations

from agentic_engineer.graph.state import ExecutionGraphState


def route_after_schedule(state: ExecutionGraphState) -> str:
    if state.get("safe_stopped") or state.get("stop_reason"):
        return "safe_stop"
    if state.get("completed"):
        return "complete"
    cohort = state.get("cohort_queue") or []
    if cohort:
        return "execute_task"
    # No ready work and not complete → safe stop (stuck / empty)
    if state.get("completed"):
        return "complete"
    return "safe_stop"


def route_after_execute(state: ExecutionGraphState) -> str:
    if state.get("pending_destructive"):
        return "await_destructive"  # handled via interrupt inside node; fallback
    if state.get("pending_command"):
        return "await_command"
    if state.get("last_failure"):
        return "fail_analyze"
    if state.get("cohort_queue"):
        return "execute_task"
    return "sync"


def route_after_fail_analyze(state: ExecutionGraphState) -> str:
    if state.get("awaiting_plan_reapproval") or state.get("failure_recommendation") == "replan":
        return "replan_park"
    if state.get("safe_stopped") or state.get("failure_recommendation") == "stop":
        return "safe_stop"
    # retry: go back to schedule (task reset to pending/ready)
    return "schedule"


def route_after_sync(state: ExecutionGraphState) -> str:
    if state.get("safe_stopped"):
        return "safe_stop"
    if state.get("completed"):
        return "docs_stub"
    return "schedule"
