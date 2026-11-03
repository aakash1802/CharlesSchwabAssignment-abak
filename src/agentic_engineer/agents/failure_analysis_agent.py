"""Failure Analysis agent — advise recovery; Python owns final decision."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentic_engineer.config.settings import get_settings
from agentic_engineer.execution.recovery_engine import RecoveryDecisionEngine
from agentic_engineer.llm.base import LLMProvider
from agentic_engineer.llm.failures import FailureCategory
from agentic_engineer.models.execution import FailureRecommendation
from agentic_engineer.models.recovery import (
    RecoveryAttempt,
    RecoveryDecision,
    RecoveryStrategy,
)
from agentic_engineer.models.task import Task


@dataclass(frozen=True)
class FailureAnalysisResult:
    recommendation: FailureRecommendation
    reason: str
    replan_stub: bool = False
    plan_patch: dict[str, Any] = field(default_factory=dict)
    failure_category: FailureCategory | None = None
    strategy: RecoveryStrategy | None = None
    decision: RecoveryDecision | None = None


class FailureAnalysisAgent:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider
        self._engine = RecoveryDecisionEngine(provider)

    def analyze(
        self,
        *,
        task: Task,
        error: str,
        max_retries: int | None = None,
        prefer_replan: bool = False,
        failure_category: FailureCategory | str | None = None,
        history: list[RecoveryAttempt] | None = None,
        llm_suggestion: RecoveryStrategy | str | None = None,
        consult_llm: bool = False,
    ) -> FailureAnalysisResult:
        decision = self._engine.decide(
            task=task,
            error=error,
            history=history or [],
            failure_category=failure_category,
            prefer_replan=prefer_replan,
            llm_suggestion=llm_suggestion,
            max_retries=max_retries
            if max_retries is not None
            else get_settings().max_task_retries,
            consult_llm=consult_llm,
        )
        legacy = decision.to_legacy_recommendation()
        plan_patch: dict[str, Any] = {}
        if decision.strategy == RecoveryStrategy.REPLAN:
            plan_patch = {
                "failed_task_id": task.id,
                "invalidate_downstream": True,
                "note": (
                    f"Material replan after recovery decision on {task.id}: {error}"
                ),
                "failure_category": decision.failure_category.value,
            }
        return FailureAnalysisResult(
            recommendation=legacy,  # type: ignore[arg-type]
            reason=decision.rationale or decision.failure_explanation,
            replan_stub=False,
            plan_patch=plan_patch,
            failure_category=decision.failure_category,
            strategy=decision.strategy,
            decision=decision,
        )
