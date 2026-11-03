"""AC-P4-1 / AC-P4-2 — sequential deps + logical parallel cohorts."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.graph.requirement_workflow import RequirementWorkflowService
from agentic_engineer.llm import MockProvider
from agentic_engineer.workspace import Workspace


def _approve_to_plan(service: RequirementWorkflowService) -> None:
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    service.approve(comment="spec ok")
    assert service.load_active().status == "awaiting_plan_approval"
    service.approve(comment="plan ok")
    assert service.load_active().status == "plan_approved"


def _drive_execution_approving_commands(
    service: RequirementWorkflowService,
) -> None:
    state = service.start_execution()
    # Approve command + release gates until terminal.
    guard = 0
    while state.status in {
        "awaiting_command_approval",
        "awaiting_release_approval",
    } and guard < 12:
        state = service.approve(comment="ok")
        guard += 1
    assert state.status == "completed", state.status


def test_sequential_dependency_order(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "seq")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    _approve_to_plan(service)
    _drive_execution_approving_commands(service)

    state = service.load_active()
    assert state.plan is not None
    by_id = {t.id: t for t in state.plan.tasks}
    assert by_id["t1"].status == "completed"
    assert by_id["t2"].status == "completed"
    assert by_id["t3"].status == "completed"
    assert by_id["t4"].status == "completed"
    # t2 depends on t1; t3/t4 depend on t2 — all completed implies order was respected.
    assert (ws.root / "src" / "generated" / "t3.py").is_file()
    assert (ws.root / "src" / "generated" / "t4.py").is_file()


def test_logical_parallel_cohort(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "par")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    _approve_to_plan(service)
    _drive_execution_approving_commands(service)

    state = service.load_active()
    assert state.status == "completed"
    # Phase markdown for cohorts exists (inspect + cohort syncs).
    phases = list((ws.agentic_dir / "readable" / "phases").glob("*.md"))
    names = {p.name for p in phases}
    assert any(n.endswith("_inspect.md") for n in names)
    assert any("cohort_" in n for n in names)
    # Independent t3∥t4 both completed; dependents t5/t6 completed after.
    statuses = {t.id: t.status for t in state.plan.tasks}  # type: ignore[union-attr]
    assert statuses["t3"] == "completed"
    assert statuses["t4"] == "completed"
    assert statuses["t5"] == "completed"
    assert statuses["t6"] == "completed"
