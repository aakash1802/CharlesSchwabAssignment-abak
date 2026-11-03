"""Engineering task records for the dependency graph (Phase 3)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from agentic_engineer.models.common import utc_now

TaskStatus = Literal[
    "pending",
    "ready",
    "in_progress",
    "completed",
    "failed",
    "blocked",
]


class Task(BaseModel):
    """A single engineering task with explicit dependencies."""

    id: str
    name: str
    description: str = ""
    depends_on: list[str] = Field(default_factory=list)
    status: TaskStatus = "pending"
    agent: str = "developer"
    acceptance_criteria: list[str] = Field(default_factory=list)
    max_retries: int = 2
    retry_count: int = 0
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    error: str | None = None
    recovery_feedback: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
