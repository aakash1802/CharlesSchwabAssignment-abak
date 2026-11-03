"""Documentation agent — LLM or stub notes (Phase 5)."""

from __future__ import annotations

import json

from agentic_engineer.agents.codegen_context import (
    CodegenContext,
    build_codegen_context,
    is_mock_without_queue,
    parse_files_payload,
)
from agentic_engineer.agents.prompt_loader import load_prompt
from agentic_engineer.llm.base import LLMError, LLMProvider, LLMRequest
from agentic_engineer.llm.json_extract import describe_json_error, extract_json_text
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.specification import Specification
from agentic_engineer.models.task import Task
from agentic_engineer.workspace.workspace import Workspace


def _stub_task_notes(workspace: Workspace, task: Task) -> list[str]:
    rel = f"docs/generated/{task.id}.md"
    body = (
        f"# {task.name}\n\n"
        f"Documentation notes for task `{task.id}`.\n\n"
        f"{task.description.strip() or '_No description_'}\n\n"
        "## Acceptance criteria\n\n"
    )
    if task.acceptance_criteria:
        body += "\n".join(f"- {c}" for c in task.acceptance_criteria) + "\n"
    else:
        body += "_None_\n"
    workspace.write_text(rel, body)
    return [rel]


def _stub_product_notes(
    workspace: Workspace,
    plan: EngineeringPlan,
    design_note: str,
) -> list[str]:
    rel = "docs/AGENTIC_NOTES.md"
    lines = [
        "# Project notes",
        "",
        f"Generated from plan `{plan.id}`.",
        "",
        "## Summary",
        "",
        plan.summary.strip() or "_Empty_",
        "",
        "## Design",
        "",
        design_note.strip() or "_None_",
        "",
        "## Tasks",
        "",
    ]
    for task in plan.tasks:
        lines.append(f"- `{task.id}` [{task.status}] {task.name}")
    lines.append("")
    workspace.write_text(rel, "\n".join(lines))
    return [rel]


class DocumentationAgent:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider
        self._system = load_prompt("documentation_agent.txt")

    def write_stub(
        self,
        *,
        workspace: Workspace,
        task: Task,
        context: CodegenContext | None = None,
    ) -> list[str]:
        """Backward-compatible per-task note (used when a docs task runs)."""
        return self.write_task_notes(workspace=workspace, task=task, context=context)

    def write_task_notes(
        self,
        *,
        workspace: Workspace,
        task: Task,
        context: CodegenContext | None = None,
    ) -> list[str]:
        if self._provider is None or is_mock_without_queue(self._provider):
            return _stub_task_notes(workspace, task)
        return self._llm_write_files(
            workspace=workspace,
            context=context or CodegenContext(task=task),
            label=task.id,
        )

    def write_product_notes(
        self,
        *,
        workspace: Workspace,
        plan: EngineeringPlan,
        design_note: str = "",
        specification: Specification | None = None,
    ) -> list[str]:
        """Product-facing notes under the target (no CLI dependency)."""
        if self._provider is None or is_mock_without_queue(self._provider):
            return _stub_product_notes(workspace, plan, design_note)

        # Synthetic task so CodegenContext can carry plan/spec for README generation.
        task = Task(
            id="docs_product",
            name="Write product documentation",
            description=(
                "Write README.md and any needed docs covering setup, configuration, "
                "API usage, and assumptions for the delivered application."
            ),
            agent="documentation",
            acceptance_criteria=[
                "README documents setup and configuration",
                "API usage examples included when endpoints exist",
                "Assumptions and limitations documented",
            ],
        )
        context = build_codegen_context(
            workspace=workspace,
            task=task,
            plan=plan,
            specification=specification,
            design_note=design_note,
        )
        return self._llm_write_files(
            workspace=workspace, context=context, label="product_notes"
        )

    def _llm_write_files(
        self,
        *,
        workspace: Workspace,
        context: CodegenContext,
        label: str,
    ) -> list[str]:
        assert self._provider is not None
        request = LLMRequest(
            prompt=context.to_prompt_json() + "\n\nReturn JSON only.",
            system=self._system,
            response_schema_name="DocumentationFiles",
        )
        try:
            response = self._provider.complete(request)
            data = json.loads(extract_json_text(response.text))
            files = parse_files_payload(data)
            written: list[str] = []
            for path, content in files:
                workspace.write_text(path, content)
                written.append(path)
            return written
        except (LLMError, json.JSONDecodeError, ValueError, TypeError, OSError) as exc:
            detail = describe_json_error(exc) if isinstance(exc, json.JSONDecodeError) else str(exc)
            raise LLMError(f"Documentation agent failed for {label}: {detail}") from exc
