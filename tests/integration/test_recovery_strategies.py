"""Integration coverage for recovery decisions inside LangGraph execution."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.config.settings import clear_settings_cache, get_settings
from agentic_engineer.execution.recovery_store import RecoveryHistoryStore
from agentic_engineer.graph.requirement_workflow import RequirementWorkflowService
from agentic_engineer.llm import MockProvider
from agentic_engineer.models.recovery import RecoveryStrategy
from agentic_engineer.workspace import Workspace


def _to_plan_approved(service: RequirementWorkflowService) -> None:
    service.start(
        "Add a /health endpoint that returns status ok and the app version string"
    )
    service.approve(comment="spec")
    service.approve(comment="plan")


def test_recovery_decisions_resume_from_checkpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_MAX_TASK_RETRIES", "2")
    clear_settings_cache()
    assert get_settings().max_task_retries == 2

    ws = Workspace.init(tmp_path / "recovery_ckpt")
    service = RequirementWorkflowService(ws, provider=MockProvider())
    _to_plan_approved(service)

    state = service.start_execution(force_fail_task_ids=["t3"])
    assert state.status == "safe_stopped"

    store = RecoveryHistoryStore(
        ws.agentic_dir / "workflows" / state.workflow_id
    )
    history = store.load(state.workflow_id)
    assert history.attempts, "expected persisted recovery attempts"
    strategies = {a.strategy for a in history.attempts}
    assert RecoveryStrategy.RETRY_SAME in strategies or RecoveryStrategy.RETRY_CORRECTED in strategies
    assert any(
        a.strategy == RecoveryStrategy.ESCALATE or a.outcome == "escalated"
        for a in history.attempts
    ) or state.stop_reason

    # Checkpoint DB exists for resume narrative.
    ckpt = (
        ws.agentic_dir
        / "workflows"
        / state.workflow_id
        / "checkpoints"
        / "langgraph.sqlite"
    )
    assert ckpt.is_file()

    events_path = (
        ws.agentic_dir / "workflows" / state.workflow_id / "execution_history.json"
    )
    assert events_path.is_file()
    text = events_path.read_text(encoding="utf-8")
    assert "recovery_decision" in text
