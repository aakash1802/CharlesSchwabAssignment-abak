"""Persisted requirement/execution workflow state (Phases 2–4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from agentic_engineer.models.approval import WorkflowStatus
from agentic_engineer.models.common import utc_now
from agentic_engineer.models.execution import (
    CommandEvidence,
    CommandProposal,
    DestructiveProposal,
)
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.requirements import ClarificationAnswer, RequirementAnalysis
from agentic_engineer.models.specification import Specification


class RequirementWorkflowState(BaseModel):
    schema_version: int = 1
    workflow_id: str
    requirement: str
    status: WorkflowStatus = "analyzing"
    analysis: RequirementAnalysis | None = None
    clarification_answers: list[ClarificationAnswer] = Field(default_factory=list)
    specification_id: str | None = None
    specification: Specification | None = None
    plan_id: str | None = None
    plan: EngineeringPlan | None = None
    pending_approval_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    stop_reason: str | None = None
    # Phase 4 execution mirror (JSON); LangGraph checkpointer is resume source of truth.
    execution_thread_id: str | None = None
    design_note: str | None = None
    current_cohort_ids: list[str] = Field(default_factory=list)
    cohort_index: int = 0
    next_phase_index: int = 7
    pending_command: CommandProposal | None = None
    pending_destructive: DestructiveProposal | None = None
    test_results: list[CommandEvidence] = Field(default_factory=list)
    force_fail_task_ids: list[str] = Field(default_factory=list)
    force_replan_task_ids: list[str] = Field(default_factory=list)
    plan_patch: dict[str, Any] | None = None
