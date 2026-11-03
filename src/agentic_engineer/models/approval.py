"""Human approval records — decisions are never LLM-authored."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from agentic_engineer.models.common import utc_now


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ApprovalType(str, Enum):
    SPECIFICATION = "specification"
    PLAN = "plan"
    COMMAND = "command"
    DESTRUCTIVE = "destructive"
    RELEASE = "release"


class ApprovalRecord(BaseModel):
    id: str
    workflow_id: str
    approval_type: ApprovalType
    requested_action: str
    decision: ApprovalDecision = ApprovalDecision.PENDING
    comment: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    decided_at: datetime | None = None
    artifact_ref: str | None = None


WorkflowStatus = Literal[
    "analyzing",
    "awaiting_clarification",
    "generating_spec",
    "awaiting_spec_approval",
    "spec_approved",
    "spec_rejected",
    "planning",
    "awaiting_plan_approval",
    "plan_approved",
    "plan_rejected",
    "executing",
    "awaiting_command_approval",
    "awaiting_destructive_approval",
    "awaiting_release_approval",
    "safe_stopped",
    "completed",
    "stopped",
]
