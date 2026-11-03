"""Structured Developer Agent response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


FileAction = Literal["create", "modify"]


class GeneratedFile(BaseModel):
    """One file the Developer Agent intends to create or modify."""

    path: str = Field(description="Workspace-relative path")
    content: str = Field(description="Full file text")
    action: FileAction = Field(
        default="create",
        description="Whether this path is new or an update to an existing file",
    )

    @field_validator("path")
    @classmethod
    def _strip_path(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("path must be non-empty")
        return text


class DeveloperFilesResponse(BaseModel):
    """
    Strict structured output for Developer Agent batches.

    `more_files_remaining` lets the agent emit related files across bounded
    batches without exceeding provider token limits.
    """

    summary: str = Field(default="", description="Short summary of this batch")
    files: list[GeneratedFile] = Field(default_factory=list)
    implementation_decisions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    more_files_remaining: bool = Field(
        default=False,
        description="True when additional related files are still needed",
    )

    @field_validator("files")
    @classmethod
    def _require_files_when_complete(cls, value: list[GeneratedFile]) -> list[GeneratedFile]:
        return value


def developer_files_json_schema() -> dict[str, Any]:
    """JSON Schema for Anthropic structured outputs / tool input_schema."""
    schema = DeveloperFilesResponse.model_json_schema()
    # Anthropic prefers a root object without $defs confusion; keep as-is and
    # ensure additionalProperties is false on the root when present.
    if schema.get("type") == "object" and "additionalProperties" not in schema:
        schema["additionalProperties"] = False
    schema["title"] = "DeveloperFiles"
    return schema
