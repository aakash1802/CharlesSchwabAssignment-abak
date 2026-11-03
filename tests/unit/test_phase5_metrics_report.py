"""Phase 5 — metrics from events + report artifacts + revert refuse."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.audit.metrics import derive_metrics
from agentic_engineer.config.settings import clear_settings_cache
from agentic_engineer.execution.events import ExecutionEventLog
from agentic_engineer.graph.requirement_workflow import RequirementWorkflowService
from agentic_engineer.llm import MockProvider
from agentic_engineer.models.execution import ExecutionEvent
from agentic_engineer.workspace import Workspace


def test_derive_metrics_never_fabricates_latency() -> None:
    events = [
        ExecutionEvent(event_type="task_start", message="a"),
        ExecutionEvent(event_type="task_finish", message="b"),
        ExecutionEvent(event_type="retry", message="c"),
    ]
    snap = derive_metrics("workflow_x", events)
    assert snap.task_starts == 1
    assert snap.task_finishes == 1
    assert snap.retries == 1
    assert snap.insufficient_data
    assert any("latency" in item.lower() or "MTTR" in item for item in snap.insufficient_data)


def test_report_and_history_after_success(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "rep")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    service.approve(comment="spec")
    service.approve(comment="plan")
    state = service.start_execution()
    guard = 0
    while state.status in {
        "awaiting_command_approval",
        "awaiting_release_approval",
    } and guard < 12:
        state = service.approve(comment="ok")
        guard += 1
    assert state.status == "completed"

    service.write_report()
    report_json = ws.agentic_dir / "reports" / f"report_{state.workflow_id}.json"
    assert report_json.is_file()
    assert (ws.agentic_dir / "readable" / "REPORT.md").is_file()
    metrics = ws.agentic_dir / "workflows" / state.workflow_id / "metrics.json"
    assert metrics.is_file()
    history = ws.agentic_dir / "workflows" / state.workflow_id / "execution_history.json"
    assert history.is_file()
    text = service.format_history()
    assert "task_start" in text or "inspect_complete" in text
    assert "Refused" in service.refuse_file_revert()


def test_safe_stop_skips_release_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_MAX_TASK_RETRIES", "2")
    clear_settings_cache()
    ws = Workspace.init(tmp_path / "safe")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    service.approve(comment="spec")
    service.approve(comment="plan")
    state = service.start_execution(force_fail_task_ids=["t3"])
    assert state.status == "safe_stopped"
    assert state.status != "awaiting_release_approval"
    report_json = ws.agentic_dir / "reports" / f"report_{state.workflow_id}.json"
    assert report_json.is_file()


def test_material_replan_uses_plan_gate(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "replan")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    service.approve(comment="spec")
    service.approve(comment="plan")
    state = service.start_execution(
        force_fail_task_ids=["t3"],
        force_replan_task_ids=["t3"],
    )
    # Drive command gates until replan parks at plan approval.
    guard = 0
    while state.status == "awaiting_command_approval" and guard < 10:
        state = service.approve(comment="cmd")
        guard += 1
    # Exhaust retries then replan park (force_fail until continue_after_replan clears it).
    assert state.status == "awaiting_plan_approval", (
        state.status,
        state.stop_reason,
        state.plan_patch,
    )
    assert state.plan_patch is not None
    assert state.plan_patch.get("material") is True
    events = ExecutionEventLog(ws.agentic_dir / "workflows" / state.workflow_id).list_events()
    assert any(e.event_type == "replan" for e in events)

    # Approve replan → continue; force_fail cleared so tasks can complete.
    state = service.approve(comment="replan ok")
    guard = 0
    while state.status in {
        "awaiting_command_approval",
        "awaiting_release_approval",
        "awaiting_plan_approval",
    } and guard < 15:
        state = service.approve(comment="ok")
        guard += 1
    assert state.status == "completed", state.status
