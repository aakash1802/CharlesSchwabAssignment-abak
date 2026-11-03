"""Execution-phase records: command proposals, evidence, audit events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from agentic_engineer.models.common import utc_now

CommandKind = Literal["argv", "shell"]
FailureRecommendation = Literal["retry", "stop", "replan"]


class CommandProposal(BaseModel):
    """Agent-proposed command awaiting human approve/reject."""

    proposal_id: str
    kind: CommandKind = "argv"
    argv: list[str] = Field(default_factory=list)
    shell: str | None = None
    cwd_relative: str = "."
    reason: str = ""
    task_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class CommandEvidence(BaseModel):
    """Captured result of an approved command run."""

    proposal_id: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    approved: bool = True
    task_id: str | None = None
    recorded_at: datetime = Field(default_factory=utc_now)

    @property
    def passed(self) -> bool:
        return self.approved and not self.timed_out and self.exit_code == 0


class DestructiveProposal(BaseModel):
    """High-impact filesystem action awaiting human approve/reject."""

    proposal_id: str
    action: str
    paths: list[str] = Field(default_factory=list)
    reason: str = ""
    task_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ExecutionEvent(BaseModel):
    """Minimal append-only execution audit event."""

    event_type: str
    message: str = ""
    task_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
