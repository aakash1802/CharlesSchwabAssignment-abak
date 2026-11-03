"""Unit tests for intelligent failure recovery strategies."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.config.settings import clear_settings_cache
from agentic_engineer.execution.recovery_engine import RecoveryDecisionEngine
from agentic_engineer.execution.recovery_policy import (
    decide_strategy,
    validate_llm_recommendation,
)
from agentic_engineer.execution.recovery_store import RecoveryHistoryStore
from agentic_engineer.execution.replan import apply_material_plan_patch
from agentic_engineer.execution.scope_reduce import apply_scope_reduction
from agentic_engineer.graph.dependency import validate_graph
from agentic_engineer.llm.failures import FailureCategory
from agentic_engineer.llm.mock import MockProvider
from agentic_engineer.models.recovery import (
    RecoveryAttempt,
    RecoveryBudgets,
    RecoveryDecision,
    RecoveryStrategy,
)
from agentic_engineer.models.task import Task


def _task(**kwargs) -> Task:
    base = {
        "id": "t1",
        "name": "Implement feature",
        "description": "Build scaffolding, config, and persistence",
        "acceptance_criteria": ["scaffold", "config", "persistence", "tests"],
    }
    base.update(kwargs)
    return Task(**base)


def test_network_timeout_selects_retry_same() -> None:
    decision = decide_strategy(
        category=FailureCategory.TRANSIENT_PROVIDER,
        error="network timeout talking to provider",
        history=[],
        budgets=RecoveryBudgets(),
    )
    assert decision.strategy == RecoveryStrategy.RETRY_SAME
    assert decision.inputs_must_change is False


def test_invalid_json_selects_retry_corrected() -> None:
    decision = decide_strategy(
        category=FailureCategory.INVALID_STRUCTURED_OUTPUT,
        error="LLM returned invalid JSON",
        history=[],
        budgets=RecoveryBudgets(),
    )
    assert decision.strategy == RecoveryStrategy.RETRY_CORRECTED
    assert decision.inputs_must_change is True
    assert "feedback" in decision.proposed_corrective_action.lower() or (
        "Correct" in decision.proposed_corrective_action
        or "feedback" in decision.proposed_corrective_action.lower()
    )


def test_truncated_response_selects_reduce_scope() -> None:
    decision = decide_strategy(
        category=FailureCategory.OUTPUT_TRUNCATED,
        error="Model response truncated (stop_reason=max_tokens)",
        history=[],
        budgets=RecoveryBudgets(),
    )
    assert decision.strategy == RecoveryStrategy.REDUCE_SCOPE
    assert decision.scope_changes is True
    assert decision.dependency_graph_changes is True


def test_repeated_implementation_failure_selects_replan() -> None:
    history = [
        RecoveryAttempt(
            workflow_id="wf",
            task_id="t1",
            attempt_number=1,
            failure_category=FailureCategory.IMPLEMENTATION_ERROR,
            strategy=RecoveryStrategy.RETRY_CORRECTED,
            outcome="failed",
        )
    ]
    decision = decide_strategy(
        category=FailureCategory.IMPLEMENTATION_ERROR,
        error="generated code raises TypeError",
        history=history,
        budgets=RecoveryBudgets(),
    )
    assert decision.strategy == RecoveryStrategy.REPLAN
    assert decision.human_approval_required is True


def test_workspace_violation_selects_escalate() -> None:
    decision = decide_strategy(
        category=FailureCategory.WORKSPACE_VIOLATION,
        error="Path escapes workspace",
        history=[],
        budgets=RecoveryBudgets(),
    )
    assert decision.strategy == RecoveryStrategy.ESCALATE
    assert decision.human_approval_required is True
    assert decision.llm_may_approve is False


def test_repeated_ineffective_retry_triggers_escalation_ladder() -> None:
    history = [
        RecoveryAttempt(
            workflow_id="wf",
            task_id="t1",
            attempt_number=1,
            failure_category=FailureCategory.INVALID_STRUCTURED_OUTPUT,
            strategy=RecoveryStrategy.RETRY_CORRECTED,
            outcome="failed",
        )
    ]
    decision = decide_strategy(
        category=FailureCategory.INVALID_STRUCTURED_OUTPUT,
        error="invalid JSON again",
        history=history,
        budgets=RecoveryBudgets(),
    )
    # Same strategy already failed → escalate (splitting does not fix JSON shape)
    assert decision.strategy == RecoveryStrategy.ESCALATE
    assert decision.human_approval_required is True


def test_lineage_scope_budget_exhausts_across_nested_ids() -> None:
    from agentic_engineer.execution.scope_reduce import lineage_task_ids

    assert lineage_task_ids("t7_s1_s1") == ["t7", "t7_s1", "t7_s1_s1"]
    history = [
        RecoveryAttempt(
            workflow_id="wf",
            task_id="t7",
            attempt_number=1,
            failure_category=FailureCategory.OUTPUT_TRUNCATED,
            strategy=RecoveryStrategy.REDUCE_SCOPE,
            outcome="failed",
        ),
        RecoveryAttempt(
            workflow_id="wf",
            task_id="t7_s1",
            attempt_number=1,
            failure_category=FailureCategory.OUTPUT_TRUNCATED,
            strategy=RecoveryStrategy.REDUCE_SCOPE,
            outcome="failed",
        ),
    ]
    decision = decide_strategy(
        category=FailureCategory.OUTPUT_TRUNCATED,
        error="Model response truncated (stop_reason=max_tokens)",
        history=history,
        budgets=RecoveryBudgets(max_scope_reductions=2),
    )
    assert decision.strategy == RecoveryStrategy.ESCALATE


def test_invalid_json_message_is_not_classified_as_truncated() -> None:
    from agentic_engineer.llm.failures import classify_from_message

    msg = (
        "Documentation agent failed for t7: LLM returned invalid JSON "
        "(Expecting ',' delimiter at line 3 column 10)."
    )
    assert classify_from_message(msg) == FailureCategory.INVALID_STRUCTURED_OUTPUT
    unterminated = (
        "Documentation agent failed for t7_s1: LLM returned invalid JSON "
        "(Unterminated string starting at at line 6 column 18)."
    )
    assert classify_from_message(unterminated) == FailureCategory.OUTPUT_TRUNCATED


def test_recovery_budget_exhaustion_triggers_escalate() -> None:
    history = [
        RecoveryAttempt(
            workflow_id="wf",
            task_id="t1",
            attempt_number=i,
            failure_category=FailureCategory.TRANSIENT_PROVIDER,
            strategy=RecoveryStrategy.RETRY_SAME,
            outcome="failed",
        )
        for i in range(1, 6)
    ]
    decision = decide_strategy(
        category=FailureCategory.TRANSIENT_PROVIDER,
        error="timeout",
        history=history,
        budgets=RecoveryBudgets(max_total_recovery_attempts=5),
    )
    assert decision.strategy == RecoveryStrategy.ESCALATE
    assert "budget exhausted" in decision.rationale.lower() or "exhausted" in (
        decision.rationale.lower()
    )


def test_recovery_history_persists_across_restart(tmp_path: Path) -> None:
    store = RecoveryHistoryStore(tmp_path / "wf")
    attempt = RecoveryAttempt(
        workflow_id="wf1",
        task_id="t1",
        attempt_number=1,
        failure_category=FailureCategory.RATE_LIMIT,
        strategy=RecoveryStrategy.RETRY_SAME,
        strategy_rationale="backoff",
        outcome="failed",
    )
    store.append("wf1", attempt)
    reloaded = RecoveryHistoryStore(tmp_path / "wf").load("wf1")
    assert len(reloaded.attempts) == 1
    assert reloaded.attempts[0].strategy == RecoveryStrategy.RETRY_SAME
    assert reloaded.attempts[0].failure_category == FailureCategory.RATE_LIMIT


def test_corrected_retry_changes_request() -> None:
    engine = RecoveryDecisionEngine(MockProvider())
    decision = engine.decide(
        task=_task(),
        error="LLM returned invalid JSON: Expecting ',' delimiter",
        history=[],
        failure_category=FailureCategory.INVALID_STRUCTURED_OUTPUT,
    )
    assert decision.strategy == RecoveryStrategy.RETRY_CORRECTED
    feedback = engine.corrective_feedback(decision)
    assert "invalid JSON" in feedback or "Failure" in feedback
    assert "Do not repeat" in feedback
    # Task annotation would change the next prompt payload.
    task = _task(recovery_feedback=feedback)
    assert task.recovery_feedback != _task().recovery_feedback
    assert "Prior attempt failed" in (task.recovery_feedback or "")


def test_scope_reduction_creates_valid_dependent_subtasks() -> None:
    tasks = [
        _task(id="t1", depends_on=[]),
        Task(
            id="t2",
            name="Tests",
            description="test",
            depends_on=["t1"],
            agent="testing",
        ),
    ]
    updated, summary = apply_scope_reduction(
        tasks, failed_task_id="t1", note="too many files"
    )
    assert summary["applied"] is True
    assert len(summary["created_task_ids"]) >= 2
    assert validate_graph(updated).ok
    # Downstream now depends on the final subtask, not the removed parent.
    t2 = next(t for t in updated if t.id == "t2")
    assert "t1" not in t2.depends_on
    assert summary["final_task_id"] in t2.depends_on
    # Chain: first subtask ready, second depends on first.
    created = [t for t in updated if t.id in summary["created_task_ids"]]
    assert created[0].depends_on == []
    assert created[1].depends_on == [created[0].id]


def test_replanning_preserves_unaffected_completed_tasks() -> None:
    tasks = [
        Task(id="t1", name="A", description="a", status="completed"),
        Task(id="t2", name="B", description="b", depends_on=["t1"], status="failed"),
        Task(id="t3", name="C", description="c", depends_on=["t2"], status="pending"),
        Task(id="t4", name="D", description="d", status="completed"),
    ]
    patched, summary = apply_material_plan_patch(
        tasks, failed_task_id="t2", note="redesign B"
    )
    assert summary["applied"] is True
    by_id = {t.id: t for t in patched}
    assert by_id["t1"].status == "completed"
    assert by_id["t4"].status == "completed"
    assert by_id["t2"].status == "pending"
    assert by_id["t3"].status == "pending"
    assert "t1" not in summary["invalidated_task_ids"]
    assert "t4" not in summary["invalidated_task_ids"]


def test_dependency_failure_selects_retry_corrected() -> None:
    decision = decide_strategy(
        category=FailureCategory.DEPENDENCY_FAILURE,
        error="ModuleNotFoundError: No module named 'sqlalchemy'",
        history=[],
        budgets=RecoveryBudgets(),
    )
    assert decision.strategy == RecoveryStrategy.RETRY_CORRECTED
    assert decision.human_approval_required is False
    assert "install" in decision.proposed_corrective_action.lower()


def test_dependency_failure_escalates_after_corrected_retry() -> None:
    history = [
        RecoveryAttempt(
            workflow_id="wf",
            task_id="t1",
            attempt_number=1,
            failure_category=FailureCategory.DEPENDENCY_FAILURE,
            strategy=RecoveryStrategy.RETRY_CORRECTED,
            outcome="failed",
        )
    ]
    decision = decide_strategy(
        category=FailureCategory.DEPENDENCY_FAILURE,
        error="ModuleNotFoundError: No module named 'sqlalchemy'",
        history=history,
        budgets=RecoveryBudgets(),
    )
    assert decision.strategy == RecoveryStrategy.ESCALATE
    assert decision.human_approval_required is True


def test_dependency_corrective_feedback_mentions_install() -> None:
    engine = RecoveryDecisionEngine(MockProvider())
    decision = decide_strategy(
        category=FailureCategory.DEPENDENCY_FAILURE,
        error="ModuleNotFoundError: No module named 'sqlalchemy'",
        history=[],
        budgets=RecoveryBudgets(),
    )
    feedback = engine.corrective_feedback(decision)
    assert "dependency_failure" in feedback
    assert "install" in feedback.lower()
    assert "pip" in feedback.lower()


def test_human_approval_required_for_replan() -> None:
    history = [
        RecoveryAttempt(
            workflow_id="wf",
            task_id="t1",
            attempt_number=1,
            failure_category=FailureCategory.IMPLEMENTATION_ERROR,
            strategy=RecoveryStrategy.RETRY_CORRECTED,
            outcome="failed",
        )
    ]
    decision = decide_strategy(
        category=FailureCategory.IMPLEMENTATION_ERROR,
        error="generated code raises TypeError",
        history=history,
        budgets=RecoveryBudgets(),
    )
    assert decision.strategy == RecoveryStrategy.REPLAN
    assert decision.human_approval_required is True


def test_llm_cannot_approve_its_own_recovery() -> None:
    deterministic = RecoveryDecision(
        strategy=RecoveryStrategy.ESCALATE,
        failure_category=FailureCategory.WORKSPACE_VIOLATION,
        failure_explanation="escape",
        human_approval_required=True,
        llm_may_approve=False,
        rationale="escalate",
    )
    validated = validate_llm_recommendation(
        RecoveryStrategy.RETRY_SAME,
        category=FailureCategory.WORKSPACE_VIOLATION,
        deterministic=deterministic,
    )
    assert validated.strategy == RecoveryStrategy.ESCALATE
    assert validated.llm_may_approve is False
    assert validated.human_approval_required is True


def test_engine_maps_legacy_truncated_alias() -> None:
    engine = RecoveryDecisionEngine(
        MockProvider(), budgets=RecoveryBudgets(max_same_retries=2)
    )
    decision = engine.decide(
        task=_task(),
        error="truncated",
        history=[],
        failure_category=FailureCategory.TRUNCATED_RESPONSE,
    )
    assert decision.failure_category == FailureCategory.OUTPUT_TRUNCATED
    assert decision.strategy == RecoveryStrategy.REDUCE_SCOPE


def test_permission_failure_escalates() -> None:
    decision = decide_strategy(
        category=FailureCategory.PERMISSION_FAILURE,
        error="permission denied writing file",
        history=[],
        budgets=RecoveryBudgets(),
    )
    assert decision.strategy == RecoveryStrategy.ESCALATE


def test_rate_limit_retry_same_with_engine() -> None:
    clear_settings_cache()
    engine = RecoveryDecisionEngine(MockProvider())
    decision = engine.decide(
        task=_task(retry_count=0),
        error="429 Too Many Requests",
        history=[],
        failure_category=FailureCategory.RATE_LIMIT,
    )
    assert decision.strategy == RecoveryStrategy.RETRY_SAME
    assert "Rate limited" in decision.rationale
