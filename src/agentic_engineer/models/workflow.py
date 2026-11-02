"""Persisted requirement-workflow state (Phase 2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from agentic_engineer.models.approval import WorkflowStatus
from agentic_engineer.models.common import utc_now
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
    pending_approval_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    stop_reason: str | None = None
