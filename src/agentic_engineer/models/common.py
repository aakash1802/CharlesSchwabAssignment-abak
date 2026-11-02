"""Common persisted models for Phase 1."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgenticProjectConfig(BaseModel):
    """Target-local `.agentic/config.json`."""

    schema_version: int = SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    active_workflow_id: str | None = None
    active_specification_id: str | None = None
    notes: str | None = None
