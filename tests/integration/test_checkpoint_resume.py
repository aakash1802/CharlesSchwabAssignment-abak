"""AC-P4-6 — resume from LangGraph checkpointer after interrupt."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.graph.requirement_workflow import RequirementWorkflowService
from agentic_engineer.llm import MockProvider
from agentic_engineer.workspace import Workspace


def test_checkpoint_resume_after_command_interrupt(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "resume")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    service.approve(comment="spec")
    service.approve(comment="plan")

    state = service.start_execution()
    assert state.status == "awaiting_command_approval"
    assert state.pending_command is not None
    assert state.execution_thread_id

    checkpoint = (
        ws.agentic_dir
        / "workflows"
        / state.workflow_id
        / "checkpoints"
        / "langgraph.sqlite"
    )
    assert checkpoint.is_file()

    # Simulate new process: fresh service, resume should restore interrupt (not re-run).
    service2 = RequirementWorkflowService(ws, provider=MockProvider())
    parked = service2.resume_execution()
    assert parked.status == "awaiting_command_approval"
    assert parked.pending_command is not None

    # Approve command + release gates until terminal complete.
    done = service2.approve(comment="ok")
    guard = 0
    while done.status in {
        "awaiting_command_approval",
        "awaiting_release_approval",
    } and guard < 8:
        done = service2.approve(comment="ok")
        guard += 1
    assert done.status == "completed"

    # Completed tasks must remain completed (no incorrect redo of durable writes).
    assert (ws.root / "src" / "generated" / "t3.py").is_file()
    assert (ws.root / "src" / "generated" / "t4.py").is_file()


def test_command_reject_does_not_execute(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "reject-cmd")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    service.approve(comment="spec")
    service.approve(comment="plan")
    state = service.start_execution()
    assert state.status == "awaiting_command_approval"
    proposal_id = state.pending_command.proposal_id  # type: ignore[union-attr]

    state = service.reject(comment="too risky")
    # Rejection fails the testing task → fail analyze → retry or stop.
    # Either way CommandRunner must not have recorded a successful run for that proposal.
    for evidence in state.test_results:
        if evidence.proposal_id == proposal_id:
            assert evidence.approved is False
            assert evidence.exit_code == -1
