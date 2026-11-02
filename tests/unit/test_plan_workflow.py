"""Plan generation and plan-approval gate (Phase 3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_engineer.graph.requirement_workflow import (
    RequirementWorkflowService,
    WorkflowError,
)
from agentic_engineer.llm import MockProvider
from agentic_engineer.workspace import Workspace


def _to_awaiting_plan_approval(service: RequirementWorkflowService) -> None:
    """Spec approve auto-advances into plan generation + plan gate."""
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    state = service.approve(comment="spec ok")
    assert state.status == "awaiting_plan_approval"


def test_spec_approve_auto_generates_plan_then_plan_approve(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    state = service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    assert state.status == "awaiting_spec_approval"

    state = service.approve(comment="spec ok")
    assert state.status == "awaiting_plan_approval"
    assert state.plan is not None
    assert state.plan_id
    assert state.pending_approval_id
    assert (ws.agentic_dir / "plans" / f"{state.plan_id}.json").is_file()
    assert (ws.agentic_dir / "plans" / f"{state.plan_id}.md").is_file()
    assert (ws.agentic_dir / "readable" / "PLAN.md").is_file()
    assert (ws.agentic_dir / "readable" / "phases" / "05_plan.md").is_file()

    approved = service.approve(comment="plan ok")
    assert approved.status == "plan_approved"
    assert approved.pending_approval_id is None
    assert (ws.agentic_dir / "readable" / "phases" / "06_plan_approval.md").is_file()
    config = ws.load_config()
    assert config.active_plan_id == approved.plan_id


def test_plan_reject(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    _to_awaiting_plan_approval(service)
    rejected = service.reject(comment="rework graph")
    assert rejected.status == "plan_rejected"


def test_plan_changes_requested_allows_regenerate(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    first = service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    first = service.approve(comment="spec ok")
    first_id = first.plan_id
    service.reject(changes_requested=True, comment="add more parallel work")
    second = service.generate_plan()
    assert second.status == "awaiting_plan_approval"
    assert second.plan_id != first_id


def test_cannot_plan_without_approved_spec(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    with pytest.raises(WorkflowError):
        service.generate_plan()


def test_plan_or_show_shows_after_approval(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    _to_awaiting_plan_approval(service)
    service.approve(comment="ok")
    shown = service.plan_or_show()
    assert shown.status == "plan_approved"
    assert shown.plan is not None
    display = service.format_plan_display(shown.plan)
    assert "flowchart TD" in display
    assert "ready:" in display
    assert "parallel_cohorts:" in display
