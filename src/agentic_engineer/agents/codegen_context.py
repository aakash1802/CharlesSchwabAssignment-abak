"""Shared context packing for LLM-driven execution agents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agentic_engineer.agents.architecture_agent import inspect_workspace
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.specification import Specification
from agentic_engineer.models.task import Task
from agentic_engineer.workspace.workspace import Workspace

_MAX_FILE_PREVIEW = 4000
_MAX_PREVIEW_FILES = 12
_SKIP_DIRS = {".agentic", ".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}


@dataclass(frozen=True)
class CodegenContext:
    """Inputs shared by developer / testing / documentation agents."""

    task: Task
    plan_summary: str = ""
    design_note: str = ""
    specification: Specification | None = None
    inspect: dict[str, object] | None = None
    file_previews: dict[str, str] | None = None

    def to_prompt_payload(self) -> dict[str, object]:
        spec_dump: dict[str, object] | None = None
        if self.specification is not None:
            spec_dump = self.specification.model_dump(mode="json")
        return {
            "task": {
                "id": self.task.id,
                "name": self.task.name,
                "description": self.task.description,
                "agent": self.task.agent,
                "acceptance_criteria": list(self.task.acceptance_criteria),
            },
            "plan_summary": self.plan_summary,
            "design_note": self.design_note,
            "specification": spec_dump,
            "workspace_inspect": self.inspect or {},
            "existing_files": self.file_previews or {},
        }

    def to_prompt_json(self) -> str:
        return json.dumps(self.to_prompt_payload(), indent=2)


def collect_file_previews(workspace: Workspace) -> dict[str, str]:
    """Return truncated contents of a few non-agentic text files for LLM context."""
    root = workspace.root
    previews: dict[str, str] = {}
    candidates: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in {
            ".py",
            ".md",
            ".toml",
            ".txt",
            ".json",
            ".yml",
            ".yaml",
            ".ini",
            ".cfg",
            ".env.example",
        } and path.name not in {"Dockerfile", "Makefile", "requirements.txt"}:
            continue
        candidates.append(path)
        if len(candidates) >= _MAX_PREVIEW_FILES:
            break

    for path in candidates:
        rel = str(path.relative_to(root)).replace("\\", "/")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if len(text) > _MAX_FILE_PREVIEW:
            text = text[:_MAX_FILE_PREVIEW] + "\n…[truncated]…"
        previews[rel] = text
    return previews


def build_codegen_context(
    *,
    workspace: Workspace,
    task: Task,
    plan: EngineeringPlan,
    specification: Specification | None = None,
    design_note: str = "",
) -> CodegenContext:
    return CodegenContext(
        task=task,
        plan_summary=plan.summary,
        design_note=design_note,
        specification=specification,
        inspect=inspect_workspace(workspace),
        file_previews=collect_file_previews(workspace),
    )


def is_mock_without_queue(provider: object) -> bool:
    """True when MockProvider has no scripted responses (use deterministic stubs)."""
    from agentic_engineer.llm.mock import MockProvider

    return isinstance(provider, MockProvider) and not provider.has_queued_responses


def normalize_relative_path(raw: str) -> str:
    """Normalize and validate a relative workspace path for LLM-proposed writes."""
    text = (raw or "").strip().replace("\\", "/")
    if not text or text.startswith("/") or text.startswith("~"):
        raise ValueError(f"Invalid path (must be relative): {raw!r}")
    if ":" in text.split("/")[0]:
        # Windows drive letter / URL scheme
        raise ValueError(f"Invalid path (absolute or URL): {raw!r}")
    parts = [p for p in text.split("/") if p and p != "."]
    if any(p == ".." for p in parts):
        raise ValueError(f"Path escapes not allowed: {raw!r}")
    if parts and parts[0] == ".agentic":
        raise ValueError(f"Writes under .agentic/ are not allowed: {raw!r}")
    return "/".join(parts)


def parse_files_payload(data: object, *, max_files: int = 15) -> list[tuple[str, str]]:
    """Parse `{files:[{path, content}, ...]}` from LLM JSON."""
    if not isinstance(data, dict):
        raise ValueError("Payload must be a JSON object")
    raw_files = data.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("Payload must include a non-empty files array")
    if len(raw_files) > max_files:
        raise ValueError(f"Too many files ({len(raw_files)}); max is {max_files}")
    out: list[tuple[str, str]] = []
    for idx, item in enumerate(raw_files):
        if not isinstance(item, dict):
            raise ValueError(f"files[{idx}] must be an object")
        path = normalize_relative_path(str(item.get("path") or ""))
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError(f"files[{idx}].content must be a string")
        out.append((path, content))
    return out
