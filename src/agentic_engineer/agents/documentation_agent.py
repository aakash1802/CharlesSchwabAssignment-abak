"""Documentation agent — LLM or stub notes (Phase 5)."""

from __future__ import annotations

from agentic_engineer.agents.codegen_context import (
    CodegenContext,
    build_codegen_context,
    is_mock_without_queue,
    normalize_relative_path,
)
from agentic_engineer.agents.diagnostics import record_developer_attempt
from agentic_engineer.agents.prompt_loader import load_prompt
from agentic_engineer.config.settings import get_settings
from agentic_engineer.llm.base import LLMError, LLMProvider, LLMRequest
from agentic_engineer.llm.failures import ClassifiedLLMError, FailureCategory
from agentic_engineer.llm.structured_parse import parse_structured_model
from agentic_engineer.models.documentation import (
    DocumentationFilesResponse,
    documentation_files_json_schema,
)
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.specification import Specification
from agentic_engineer.models.task import Task
from agentic_engineer.workspace.workspace import Workspace

_DEFAULT_DOCS_MAX_TOKENS = 8192


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
        settings = get_settings()
        max_tokens = max(
            int(getattr(settings, "llm_max_tokens", 4096) or 4096),
            _DEFAULT_DOCS_MAX_TOKENS,
        )
        request = LLMRequest(
            prompt=(
                context.to_prompt_json()
                + "\n\nReturn JSON only. Prefer a single concise README.md "
                "(target under ~120 lines). Escape newlines in JSON strings."
            ),
            system=self._system,
            response_schema_name="DocumentationFiles",
            response_json_schema=documentation_files_json_schema(),
            max_tokens=max_tokens,
        )
        try:
            response = self._provider.complete(request)
            record_developer_attempt(
                workspace,
                task_id=label,
                attempt=1,
                provider=str((response.raw or {}).get("provider") or "unknown"),
                model=response.model or "",
                stop_reason=response.stop_reason,
                token_usage=response.usage or {},
                response_type=response.response_type or "text",
                parsing_outcome="pending",
                validation_outcome="pending",
                failure_category=None,
                retry_decision="parse",
                raw_response=response.text,
            )
            parsed = parse_structured_model(response, DocumentationFilesResponse)
            written: list[str] = []
            for item in parsed.files:
                path = normalize_relative_path(item.path)
                workspace.write_text(path, item.content)
                written.append(path)
            record_developer_attempt(
                workspace,
                task_id=label,
                attempt=1,
                provider=str((response.raw or {}).get("provider") or "unknown"),
                model=response.model or "",
                stop_reason=response.stop_reason,
                token_usage=response.usage or {},
                response_type=response.response_type or "text",
                parsing_outcome="ok",
                validation_outcome="ok",
                failure_category=None,
                retry_decision="commit",
                raw_response=None,
                extra={"written": written, "summary": parsed.summary},
            )
            return written
        except ClassifiedLLMError as exc:
            record_developer_attempt(
                workspace,
                task_id=label,
                attempt=1,
                provider="unknown",
                model="",
                stop_reason=None,
                token_usage={},
                response_type="error",
                parsing_outcome="failed",
                validation_outcome="failed",
                failure_category=exc.category.value,
                retry_decision="fail",
                raw_response=str(exc),
            )
            raise exc.with_prefix(f"Documentation agent failed for {label}") from exc
        except (LLMError, ValueError, TypeError, OSError) as exc:
            category = (
                FailureCategory.INVALID_STRUCTURED_OUTPUT
                if isinstance(exc, LLMError)
                else FailureCategory.UNKNOWN
            )
            raise ClassifiedLLMError(
                f"Documentation agent failed for {label}: {exc}",
                category=category,
            ) from exc
