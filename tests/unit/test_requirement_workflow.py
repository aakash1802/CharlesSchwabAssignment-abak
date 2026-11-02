"""Requirement workflow persistence, clarification, and approval."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_engineer.graph.requirement_workflow import (
    RequirementWorkflowService,
    WorkflowError,
)
from agentic_engineer.llm import MockProvider
from agentic_engineer.workspace import Workspace


def test_ambiguous_path_then_answers_then_approve(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    service = RequirementWorkflowService(ws, provider=MockProvider())

    state = service.start("Improve system security")
    assert state.status == "awaiting_clarification"
    assert state.analysis is not None
    assert state.analysis.needs_clarification

    state = service.provide_answers(
        [
            "Require API tokens on all write endpoints",
            "Must remain compatible with existing clients",
        ]
    )
    assert state.status == "awaiting_spec_approval"
    assert state.specification is not None
    assert state.pending_approval_id
    assert (ws.agentic_dir / "specifications" / f"{state.specification_id}.json").is_file()

    approved = service.approve(comment="LGTM")
    assert approved.status == "spec_approved"
    assert approved.pending_approval_id is None


def test_clear_requirement_goes_to_approval(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    state = service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    assert state.status == "awaiting_spec_approval"
    assert state.specification is not None


def test_reject_specification(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    rejected = service.reject(comment="Too vague on version format")
    assert rejected.status == "spec_rejected"


def test_cannot_approve_without_pending(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    with pytest.raises(WorkflowError):
        service.approve()
