"""Specification models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from agentic_engineer.models.common import utc_now


class Specification(BaseModel):
    """Reviewable engineering specification derived from an approved understanding."""

    id: str
    workflow_id: str
    title: str
    summary: str
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: int = 1
