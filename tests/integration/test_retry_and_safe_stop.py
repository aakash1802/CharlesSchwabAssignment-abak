"""AC-P4-5 — bounded retries then safe-stop."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.config.settings import clear_settings_cache, get_settings
from agentic_engineer.graph.requirement_workflow import RequirementWorkflowService
from agentic_engineer.llm import MockProvider
from agentic_engineer.workspace import Workspace


def _to_plan_approved(service: RequirementWorkflowService) -> None:
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    service.approve(comment="spec")
    service.approve(comment="plan")


def test_retry_cap_then_safe_stop(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_MAX_TASK_RETRIES", "2")
    clear_settings_cache()
    assert get_settings().max_task_retries == 2

    ws = Workspace.init(tmp_path / "retry")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    _to_plan_approved(service)

    # Force t3 (developer) to fail every attempt.
    state = service.start_execution(force_fail_task_ids=["t3"])
    # No command gate expected before t3 failure path completes to safe_stop.
    assert state.status == "safe_stopped", (
        state.status,
        state.stop_reason,
        [(t.id, t.status, t.retry_count, t.error) for t in (state.plan.tasks if state.plan else [])],
    )
    assert state.stop_reason
    assert "Retry cap exhausted" in state.stop_reason or "cap" in state.stop_reason.lower()

    t3 = next(t for t in state.plan.tasks if t.id == "t3")  # type: ignore[union-attr]
    assert t3.retry_count == 2
    assert t3.status == "failed"

    phases = list((ws.agentic_dir / "readable" / "phases").glob("*fail_analyze*.md"))
    assert phases, "expected fail_analyze phase markdown"
    safe = list((ws.agentic_dir / "readable" / "phases").glob("*safe_stop*.md"))
    assert safe, "expected safe_stop phase markdown"

    history = ws.agentic_dir / "workflows" / state.workflow_id / "execution_history.json"
    legacy = ws.agentic_dir / "workflows" / state.workflow_id / "execution_events.json"
    assert history.is_file() or legacy.is_file()
    # Safe-stop must not require release approval.
    assert state.status == "safe_stopped"
