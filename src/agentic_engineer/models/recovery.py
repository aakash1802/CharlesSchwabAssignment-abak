"""Failure recovery strategies, decisions, and attempt history."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from agentic_engineer.llm.failures import FailureCategory
from agentic_engineer.models.common import utc_now


class RecoveryStrategy(str, Enum):
    RETRY_SAME = "retry_same"
    RETRY_CORRECTED = "retry_corrected"
    REDUCE_SCOPE = "reduce_scope"
    REPLAN = "replan"
    ESCALATE = "escalate"


RecoveryOutcome = Literal[
    "pending",
    "succeeded",
    "failed",
    "escalated",
    "superseded",
    "awaiting_approval",
]


class RecoveryBudgets(BaseModel):
    """Python-enforced recovery limits (LLM cannot raise these)."""

    max_same_retries: int = Field(default=2, ge=0)
    max_corrected_retries: int = Field(default=2, ge=0)
    max_scope_reductions: int = Field(default=2, ge=0)
    max_replans: int = Field(default=1, ge=0)
    max_total_recovery_attempts: int = Field(default=5, ge=0)


class RecoveryDecision(BaseModel):
    """Structured recovery decision produced by the decision engine."""

    strategy: RecoveryStrategy
    failure_category: FailureCategory
    failure_explanation: str
    evidence: list[str] = Field(default_factory=list)
    proposed_corrective_action: str = ""
    inputs_must_change: bool = False
    scope_changes: bool = False
    dependency_graph_changes: bool = False
    human_approval_required: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = ""
    # Never set by an LLM — only a human approval path may clear a gate.
    llm_may_approve: bool = False

    def to_legacy_recommendation(self) -> str:
        """Map to Phase 4 FailureRecommendation literals for compatibility."""
        if self.strategy == RecoveryStrategy.REPLAN:
            return "replan"
        if self.strategy == RecoveryStrategy.ESCALATE:
            return "stop"
        return "retry"


class RecoveryAttempt(BaseModel):
    """One recorded recovery attempt for a task."""

    recovery_id: str = Field(default_factory=lambda: f"rec_{uuid4().hex[:12]}")
    workflow_id: str
    task_id: str
    attempt_number: int = 1
    failure_category: FailureCategory
    failure_details: str = ""
    strategy: RecoveryStrategy
    strategy_rationale: str = ""
    corrective_action: str = ""
    inputs_changed: bool = False
    scope_changed: bool = False
    dependency_graph_changed: bool = False
    human_approval_required: bool = False
    outcome: RecoveryOutcome = "pending"
    decision: RecoveryDecision | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class RecoveryHistory(BaseModel):
    """Append-only recovery history for a workflow (JSON-persisted)."""

    schema_version: int = 1
    workflow_id: str
    attempts: list[RecoveryAttempt] = Field(default_factory=list)

    def for_task(self, task_id: str) -> list[RecoveryAttempt]:
        return [a for a in self.attempts if a.task_id == task_id]

    def counts_for_task(self, task_id: str) -> dict[str, int]:
        attempts = self.for_task(task_id)
        return {
            "same": sum(
                1 for a in attempts if a.strategy == RecoveryStrategy.RETRY_SAME
            ),
            "corrected": sum(
                1 for a in attempts if a.strategy == RecoveryStrategy.RETRY_CORRECTED
            ),
            "scope": sum(
                1 for a in attempts if a.strategy == RecoveryStrategy.REDUCE_SCOPE
            ),
            "replan": sum(
                1 for a in attempts if a.strategy == RecoveryStrategy.REPLAN
            ),
            "escalate": sum(
                1 for a in attempts if a.strategy == RecoveryStrategy.ESCALATE
            ),
            "total": len(attempts),
        }

    def append(self, attempt: RecoveryAttempt) -> RecoveryAttempt:
        self.attempts.append(attempt)
        return attempt

    def mark_latest_outcome(
        self, task_id: str, outcome: RecoveryOutcome
    ) -> RecoveryAttempt | None:
        for attempt in reversed(self.attempts):
            if attempt.task_id == task_id and attempt.outcome == "pending":
                attempt.outcome = outcome
                return attempt
        return None

    def model_dump_persist(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
