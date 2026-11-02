"""Engineering plan models (Phase 3)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from agentic_engineer.models.common import utc_now
from agentic_engineer.models.task import Task


class EngineeringPlan(BaseModel):
    """Validated task decomposition derived from an approved specification."""

    id: str
    workflow_id: str
    specification_id: str
    summary: str
    tasks: list[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: int = 1
