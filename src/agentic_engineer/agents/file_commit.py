"""Validate-then-commit file batches (no partial writes on validation failure)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_engineer.agents.codegen_context import normalize_relative_path
from agentic_engineer.llm.failures import ClassifiedLLMError, FailureCategory
from agentic_engineer.models.developer import GeneratedFile
from agentic_engineer.workspace.paths import WorkspaceIsolationError
from agentic_engineer.workspace.workspace import Workspace


@dataclass(frozen=True)
class StagedFile:
    relative_path: str
    content: str
    action: str
    absolute_path: Path
    existed: bool
    previous_content: str | None


def validate_generated_files(
    workspace: Workspace,
    files: list[GeneratedFile],
    *,
    max_files: int,
) -> list[StagedFile]:
    """
    Parse/normalize paths, enforce workspace boundary, and stage metadata.

    Does not write. Raises ClassifiedLLMError on any invalid entry.
    """
    if not files:
        raise ClassifiedLLMError(
            "Developer response contained no files",
            category=FailureCategory.SCHEMA_VALIDATION,
        )
    if len(files) > max_files:
        raise ClassifiedLLMError(
            f"Too many files in batch ({len(files)}); max is {max_files}",
            category=FailureCategory.SCHEMA_VALIDATION,
            details={"file_count": len(files), "max_files": max_files},
        )

    staged: list[StagedFile] = []
    seen: set[str] = set()
    for idx, item in enumerate(files):
        try:
            rel = normalize_relative_path(item.path)
        except ValueError as exc:
            raise ClassifiedLLMError(
                f"files[{idx}].path invalid: {exc}",
                category=FailureCategory.WORKSPACE_SAFETY,
                details={"path": item.path},
            ) from exc
        if rel in seen:
            raise ClassifiedLLMError(
                f"Duplicate path in batch: {rel}",
                category=FailureCategory.INVALID_FILE_OPERATION,
                details={"path": rel},
            )
        seen.add(rel)
        if not isinstance(item.content, str):
            raise ClassifiedLLMError(
                f"files[{idx}].content must be a string",
                category=FailureCategory.SCHEMA_VALIDATION,
            )
        try:
            absolute = workspace.resolve(rel)
        except WorkspaceIsolationError as exc:
            raise ClassifiedLLMError(
                f"Workspace escape rejected for {rel!r}: {exc}",
                category=FailureCategory.WORKSPACE_SAFETY,
                details={"path": rel},
            ) from exc

        existed = absolute.exists() and absolute.is_file()
        previous: str | None = None
        if existed:
            try:
                previous = absolute.read_text(encoding="utf-8")
            except OSError as exc:
                raise ClassifiedLLMError(
                    f"Cannot read existing file {rel}: {exc}",
                    category=FailureCategory.INVALID_FILE_OPERATION,
                    details={"path": rel},
                ) from exc
        action = item.action
        if action == "modify" and not existed:
            action = "create"
        if action == "create" and existed:
            action = "modify"
        staged.append(
            StagedFile(
                relative_path=rel,
                content=item.content,
                action=action,
                absolute_path=absolute,
                existed=existed,
                previous_content=previous,
            )
        )
    return staged


def commit_staged_files(workspace: Workspace, staged: list[StagedFile]) -> list[str]:
    """
    Write a fully validated batch.

    On mid-write failure, restore prior contents and remove newly created files.
    """
    written: list[str] = []
    try:
        for item in staged:
            workspace.write_text(item.relative_path, item.content)
            written.append(item.relative_path)
    except OSError as exc:
        _rollback(workspace, staged, written)
        raise ClassifiedLLMError(
            f"Filesystem write failed: {exc}",
            category=FailureCategory.INVALID_FILE_OPERATION,
            details={"written_before_failure": list(written)},
        ) from exc
    return written


def _rollback(
    workspace: Workspace,
    staged: list[StagedFile],
    written: list[str],
) -> None:
    by_rel = {s.relative_path: s for s in staged}
    for rel in reversed(written):
        item = by_rel.get(rel)
        if item is None:
            continue
        try:
            if item.existed and item.previous_content is not None:
                workspace.write_text(rel, item.previous_content)
            else:
                path = item.absolute_path
                if path.is_file():
                    path.unlink()
        except OSError:
            continue
