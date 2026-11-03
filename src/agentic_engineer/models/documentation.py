"""Structured Documentation Agent response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class DocumentationFile(BaseModel):
    path: str = Field(description="Workspace-relative path")
    content: str = Field(description="Full file text")

    @field_validator("path")
    @classmethod
    def _strip_path(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("path must be non-empty")
        return text


class DocumentationFilesResponse(BaseModel):
    """Strict structured output for documentation writes."""

    summary: str = Field(default="", description="Short summary of docs written")
    files: list[DocumentationFile] = Field(default_factory=list)

    @field_validator("files")
    @classmethod
    def _require_files(cls, value: list[DocumentationFile]) -> list[DocumentationFile]:
        if not value:
            raise ValueError("files must be non-empty")
        return value


def documentation_files_json_schema() -> dict[str, Any]:
    schema = DocumentationFilesResponse.model_json_schema()
    if schema.get("type") == "object" and "additionalProperties" not in schema:
        schema["additionalProperties"] = False
    schema["title"] = "DocumentationFiles"
    return schema
