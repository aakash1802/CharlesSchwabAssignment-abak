"""Failure Recovery Decision Engine — policy + optional Failure Analysis hint."""

from __future__ import annotations

from typing import Any

from agentic_engineer.config.settings import get_settings
from agentic_engineer.execution.recovery_policy import decide_strategy
from agentic_engineer.llm.base import LLMProvider
from agentic_engineer.llm.failures import (
    FailureCategory,
    classify_from_message,
    normalize_category,
)
from agentic_engineer.models.recovery import (
    RecoveryAttempt,
    RecoveryBudgets,
    RecoveryDecision,
    RecoveryStrategy,
)
from agentic_engineer.models.task import Task


class RecoveryDecisionEngine:
    """Combine deterministic policy with optional LLM analysis recommendations.

    Budgets and approvals are always enforced in Python. The LLM cannot raise
    limits or approve its own recovery action.
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        *,
        budgets: RecoveryBudgets | None = None,
    ) -> None:
        self._provider = provider
        self._budgets = budgets

    def budgets(self) -> RecoveryBudgets:
        if self._budgets is not None:
            return self._budgets
        settings = get_settings()
        return RecoveryBudgets(
            max_same_retries=int(
                getattr(settings, "max_same_retries", 2)
            ),
            max_corrected_retries=int(
                getattr(settings, "max_corrected_retries", settings.max_structured_retries)
            ),
            max_scope_reductions=int(getattr(settings, "max_scope_reductions", 2)),
            max_replans=int(getattr(settings, "max_replans", 1)),
            max_total_recovery_attempts=int(
                getattr(settings, "max_total_recovery_attempts", 5)
            ),
        )

    def classify(
        self,
        error: str,
        failure_category: FailureCategory | str | None = None,
    ) -> FailureCategory:
        if isinstance(failure_category, FailureCategory):
            return normalize_category(failure_category)
        if isinstance(failure_category, str) and failure_category:
            try:
                return normalize_category(FailureCategory(failure_category))
            except ValueError:
                pass
        return normalize_category(classify_from_message(error))

    def decide(
        self,
        *,
        task: Task,
        error: str,
        history: list[RecoveryAttempt],
        failure_category: FailureCategory | str | None = None,
        prefer_replan: bool = False,
        llm_suggestion: RecoveryStrategy | str | None = None,
        max_retries: int | None = None,
        consult_llm: bool = False,
    ) -> RecoveryDecision:
        category = self.classify(error, failure_category)
        settings = get_settings()
        cap = max_retries if max_retries is not None else settings.max_task_retries

        suggestion = llm_suggestion
        if consult_llm and suggestion is None and self._provider is not None:
            suggestion = self._llm_suggest(
                task=task, error=error, category=category, history=history
            )

        return decide_strategy(
            category=category,
            error=error,
            history=history,
            budgets=self.budgets(),
            prefer_replan=prefer_replan,
            llm_suggestion=suggestion,
            ordinary_retry_count=task.retry_count,
            max_ordinary_retries=cap,
        )

    def build_attempt(
        self,
        *,
        workflow_id: str,
        task: Task,
        decision: RecoveryDecision,
        history: list[RecoveryAttempt],
    ) -> RecoveryAttempt:
        return RecoveryAttempt(
            workflow_id=workflow_id,
            task_id=task.id,
            attempt_number=len([a for a in history if a.task_id == task.id]) + 1,
            failure_category=decision.failure_category,
            failure_details=decision.failure_explanation,
            strategy=decision.strategy,
            strategy_rationale=decision.rationale,
            corrective_action=decision.proposed_corrective_action,
            inputs_changed=decision.inputs_must_change,
            scope_changed=decision.scope_changes,
            dependency_graph_changed=decision.dependency_graph_changes,
            human_approval_required=decision.human_approval_required,
            outcome="pending",
            decision=decision,
        )

    def corrective_feedback(self, decision: RecoveryDecision) -> str:
        """Text attached to the next attempt for RETRY_CORRECTED."""
        extra = ""
        if decision.failure_category == FailureCategory.DEPENDENCY_FAILURE:
            extra = (
                "\nMissing dependency detected. Propose a single command that installs "
                "requirements (pip install -r requirements.txt or the missing package) "
                "and then re-runs the tests/validation. Do not re-propose the same "
                "test-only command that already failed."
            )
        return (
            "Prior attempt failed. Correct the response using this feedback.\n"
            f"Failure category: {decision.failure_category.value}\n"
            f"Failure: {decision.failure_explanation}\n"
            f"Required action: {decision.proposed_corrective_action}\n"
            "Do not repeat the previous invalid output."
            f"{extra}"
        )

    def _llm_suggest(
        self,
        *,
        task: Task,
        error: str,
        category: FailureCategory,
        history: list[RecoveryAttempt],
    ) -> RecoveryStrategy | None:
        """Optional advisory call — result is validated by decide_strategy."""
        _ = self._provider
        # Advisory only for complex categories; keep offline/mock deterministic.
        if category not in {
            FailureCategory.IMPLEMENTATION_ERROR,
            FailureCategory.TEST_FAILURE,
            FailureCategory.DEPENDENCY_FAILURE,
        }:
            # UNKNOWN and others: deterministic policy owns the choice.
            return None
        prior = [a.strategy.value for a in history if a.task_id == task.id]
        if category == FailureCategory.DEPENDENCY_FAILURE:
            # Install-and-retry; escalate after a failed corrected attempt (policy).
            return RecoveryStrategy.RETRY_CORRECTED
        if prior.count(RecoveryStrategy.RETRY_CORRECTED.value) >= 1:
            return RecoveryStrategy.REPLAN
        if category == FailureCategory.TEST_FAILURE:
            return RecoveryStrategy.RETRY_CORRECTED
        return RecoveryStrategy.RETRY_CORRECTED


def decision_audit_details(decision: RecoveryDecision) -> dict[str, Any]:
    return {
        "strategy": decision.strategy.value,
        "failure_category": decision.failure_category.value,
        "failure_explanation": decision.failure_explanation,
        "evidence": list(decision.evidence),
        "proposed_corrective_action": decision.proposed_corrective_action,
        "inputs_must_change": decision.inputs_must_change,
        "scope_changes": decision.scope_changes,
        "dependency_graph_changes": decision.dependency_graph_changes,
        "human_approval_required": decision.human_approval_required,
        "confidence": decision.confidence,
        "rationale": decision.rationale,
        "llm_may_approve": False,
    }
