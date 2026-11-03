"""LangGraph nodes for Phase 4 agentic execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from langgraph.errors import GraphBubbleUp
from langgraph.types import interrupt

from agentic_engineer.agents.architecture_agent import ArchitectureAgent, inspect_workspace
from agentic_engineer.agents.developer_agent import DeveloperAgent
from agentic_engineer.agents.documentation_agent import DocumentationAgent
from agentic_engineer.agents.failure_analysis_agent import FailureAnalysisAgent
from agentic_engineer.agents.testing_agent import TestingAgent
from agentic_engineer.config.settings import get_settings
from agentic_engineer.execution.commands import CommandRunner
from agentic_engineer.execution.events import ExecutionEventLog
from agentic_engineer.execution.replan import apply_material_plan_patch
from agentic_engineer.graph.dependency import ready_tasks
from agentic_engineer.graph.state import ExecutionGraphState
from agentic_engineer.llm.base import LLMProvider
from agentic_engineer.llm.failures import ClassifiedLLMError, format_classified_message
from agentic_engineer.agents.codegen_context import build_codegen_context
from agentic_engineer.models.common import utc_now
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.specification import Specification
from agentic_engineer.models.task import Task
from agentic_engineer.persistence.readable_store import ReadableArtifactStore
from agentic_engineer.workspace.workspace import Workspace


@dataclass
class ExecutionContext:
    workspace: Workspace
    provider: LLMProvider
    plan: EngineeringPlan
    events: ExecutionEventLog
    readable: ReadableArtifactStore
    specification: Specification | None = None
    runner: CommandRunner = field(init=False)
    architecture: ArchitectureAgent = field(init=False)
    developer: DeveloperAgent = field(init=False)
    testing: TestingAgent = field(init=False)
    failure: FailureAnalysisAgent = field(init=False)
    docs: DocumentationAgent = field(init=False)

    def __post_init__(self) -> None:
        self.runner = CommandRunner(self.workspace)
        self.architecture = ArchitectureAgent(self.provider)
        self.developer = DeveloperAgent(self.provider)
        self.testing = TestingAgent(self.provider, self.runner)
        self.failure = FailureAnalysisAgent(self.provider)
        self.docs = DocumentationAgent(self.provider)

    def codegen_ctx(self, task: Task, *, design_note: str = ""):
        return build_codegen_context(
            workspace=self.workspace,
            task=task,
            plan=self.plan,
            specification=self.specification,
            design_note=design_note,
        )


def _tasks_from_state(state: ExecutionGraphState) -> list[Task]:
    return [Task.model_validate(item) for item in state.get("tasks") or []]


def _dump_tasks(tasks: list[Task]) -> list[dict[str, Any]]:
    return [t.model_dump(mode="json") for t in tasks]


def _write_phase(
    ctx: ExecutionContext,
    state: ExecutionGraphState,
    name: str,
    body: str,
) -> int:
    index = int(state.get("next_phase_index") or 7)
    ctx.readable.write_execution_phase(name, body, phase_index=index)
    return index + 1


def make_inspect_node(ctx: ExecutionContext) -> Callable[[ExecutionGraphState], dict]:
    def inspect_node(state: ExecutionGraphState) -> dict[str, Any]:
        summary = inspect_workspace(ctx.workspace)
        note = ctx.architecture.design_note(
            workspace=ctx.workspace,
            plan=ctx.plan,
            inspect=summary,
        )
        greenfield = bool(summary.get("is_greenfield"))
        ctx.events.append(
            "inspect_complete",
            message=(
                "Inspect/design complete — "
                f"{'greenfield workspace' if greenfield else 'brownfield workspace'}; "
                "architecture note ready"
            ),
            details={"is_greenfield": greenfield},
        )
        body = (
            "# Inspect / design\n\n"
            f"- Workflow: `{state.get('workflow_id')}`\n"
            f"- Greenfield: `{summary.get('is_greenfield')}`\n\n"
            "## Design note\n\n"
            f"{note}\n"
        )
        next_idx = _write_phase(ctx, state, "inspect", body)
        return {
            "inspect_summary": summary,
            "design_note": note,
            "phase": "inspect",
            "next_phase_index": next_idx,
        }

    return inspect_node


def make_schedule_node(ctx: ExecutionContext) -> Callable[[ExecutionGraphState], dict]:
    def schedule_node(state: ExecutionGraphState) -> dict[str, Any]:
        tasks = _tasks_from_state(state)
        completed = {t.id for t in tasks if t.status == "completed"}
        if len(completed) == len(tasks) and tasks:
            return {
                "completed": True,
                "phase": "schedule",
                "current_cohort": [],
                "cohort_queue": [],
            }

        ready = ready_tasks(tasks, completed_ids=completed)
        # Skip failed/blocked from ready_tasks already; also skip in_progress.
        ready = [t for t in ready if t.status not in ("failed", "blocked", "in_progress")]
        if not ready:
            # Remaining unfinished without ready set → stuck
            unfinished = [t for t in tasks if t.status != "completed"]
            if unfinished:
                return {
                    "safe_stopped": True,
                    "stop_reason": "No ready tasks remaining; graph stuck",
                    "phase": "schedule",
                    "current_cohort": [],
                    "cohort_queue": [],
                }
            return {
                "completed": True,
                "phase": "schedule",
                "current_cohort": [],
                "cohort_queue": [],
            }

        cohort_ids = [t.id for t in ready]
        for task in tasks:
            if task.id in cohort_ids:
                task.status = "ready"
                task.updated_at = utc_now()
        cohort_index = int(state.get("cohort_index") or 0)
        labels = [
            f"{t.id} ({t.name}, agent={t.agent})"
            for t in tasks
            if t.id in cohort_ids
        ]
        ctx.events.append(
            "cohort_scheduled",
            message=(
                f"Scheduling cohort {cohort_index}: "
                + ("; ".join(labels) if labels else ", ".join(cohort_ids))
            ),
            details={
                "cohort_ids": cohort_ids,
                "cohort_index": cohort_index,
            },
        )
        return {
            "tasks": _dump_tasks(tasks),
            "current_cohort": cohort_ids,
            "cohort_queue": list(cohort_ids),
            "cohort_index": cohort_index,
            "phase": "schedule",
            "completed": False,
            "last_failure": None,
            "failure_recommendation": None,
        }

    return schedule_node


def make_execute_node(ctx: ExecutionContext) -> Callable[[ExecutionGraphState], dict]:
    def execute_node(state: ExecutionGraphState) -> dict[str, Any]:
        queue = list(state.get("cohort_queue") or [])
        if not queue:
            return {"phase": "execute"}
        task_id = queue.pop(0)
        tasks = _tasks_from_state(state)
        by_id = {t.id: t for t in tasks}
        task = by_id[task_id]
        task.status = "in_progress"
        task.updated_at = utc_now()
        agent = (task.agent or "developer").lower()
        retry_note = (
            f" (retry {task.retry_count})" if task.retry_count else ""
        )
        ctx.events.append(
            "task_start",
            message=(
                f"Running {task.id} “{task.name}” via {agent} agent{retry_note}"
                + (f" — {task.description[:120]}" if task.description else "")
            ),
            task_id=task.id,
            details={"agent": agent, "retry_count": task.retry_count},
        )

        force_fail = task_id in (state.get("force_fail_task_ids") or [])
        force_destructive = task_id in (state.get("force_destructive_task_ids") or [])

        try:
            if force_fail:
                raise RuntimeError(f"Forced failure for task {task_id}")

            written = list(state.get("written_paths") or [])
            pending_command = None
            pending_destructive = None
            test_results = list(state.get("test_results") or [])
            finish_detail = ""

            if agent in {"architecture", "architect"}:
                # Architecture tasks already covered by inspect; mark complete with note.
                rel = f".agentic/artifacts/{task.id}_note.md"
                ctx.workspace.write_text(
                    rel,
                    f"# {task.name}\n\n{state.get('design_note') or '(no design note)'}\n",
                )
                written.append(rel)
                finish_detail = f"wrote architecture note {rel}"
            elif agent in {"developer", "dev"}:
                result = ctx.developer.apply_task(
                    workspace=ctx.workspace,
                    task=task,
                    force_destructive=force_destructive,
                    context=ctx.codegen_ctx(
                        task, design_note=str(state.get("design_note") or "")
                    ),
                )
                if result.destructive is not None:
                    decision = interrupt(
                        {
                            "type": "destructive",
                            "proposal": result.destructive.model_dump(mode="json"),
                        }
                    )
                    approved = bool(
                        decision.get("approved")
                        if isinstance(decision, dict)
                        else False
                    )
                    if not approved:
                        task.status = "failed"
                        task.error = "Destructive action rejected"
                        ctx.events.append(
                            "destructive_rejected",
                            message="Human rejected destructive action",
                            task_id=task.id,
                        )
                        return {
                            "tasks": _dump_tasks(tasks),
                            "cohort_queue": queue,
                            "current_task_id": task_id,
                            "pending_destructive": None,
                            "last_failure": {
                                "task_id": task.id,
                                "error": task.error,
                            },
                            "phase": "execute",
                        }
                    # Approved: record only (no actual mass delete in Phase 4 demo).
                    ctx.events.append(
                        "destructive_approved",
                        message="Human approved destructive action (recorded, not applied)",
                        task_id=task.id,
                    )
                    written.append(f"(destructive-approved:{result.destructive.action})")
                    finish_detail = f"destructive {result.destructive.action} approved"
                else:
                    written.extend(result.written_paths)
                    paths = ", ".join(result.written_paths) or "(none)"
                    finish_detail = (
                        result.summary
                        or f"wrote {len(result.written_paths)} file(s): {paths}"
                    )
            elif agent in {"testing", "test"}:
                proposal = ctx.testing.propose_for_task(
                    task,
                    context=ctx.codegen_ctx(
                        task, design_note=str(state.get("design_note") or "")
                    ),
                )
                cmd_display = (
                    proposal.shell
                    if proposal.kind == "shell"
                    else " ".join(proposal.argv)
                )
                ctx.events.append(
                    "command_proposed",
                    message=(
                        f"Proposing command for {task.id}: {cmd_display}"
                        + (f" — {proposal.reason}" if proposal.reason else "")
                    ),
                    task_id=task.id,
                    details=proposal.model_dump(mode="json"),
                )
                decision = interrupt(
                    {
                        "type": "command",
                        "proposal": proposal.model_dump(mode="json"),
                    }
                )
                approved = bool(
                    decision.get("approved") if isinstance(decision, dict) else False
                )
                if not approved:
                    evidence = ctx.runner.rejected_evidence(proposal)
                    test_results.append(evidence.model_dump(mode="json"))
                    task.status = "failed"
                    task.error = "Command rejected by human"
                    ctx.events.append(
                        "command_rejected",
                        message=(
                            f"Human rejected command for {task.id}: {cmd_display}"
                        ),
                        task_id=task.id,
                    )
                    return {
                        "tasks": _dump_tasks(tasks),
                        "cohort_queue": queue,
                        "current_task_id": task_id,
                        "pending_command": None,
                        "test_results": test_results,
                        "last_failure": {
                            "task_id": task.id,
                            "error": task.error,
                        },
                        "phase": "execute",
                    }
                ctx.events.append(
                    "command_approved",
                    message=f"Human approved command for {task.id}; running…",
                    task_id=task.id,
                )
                evidence = ctx.runner.run_approved(proposal)
                test_results.append(evidence.model_dump(mode="json"))
                ctx.events.append(
                    "command_executed",
                    message=(
                        f"Command for {task.id} finished exit={evidence.exit_code} "
                        f"({'passed' if evidence.passed else 'failed'})"
                    ),
                    task_id=task.id,
                    details={"exit_code": evidence.exit_code, "passed": evidence.passed},
                )
                finish_detail = (
                    f"command exit={evidence.exit_code} "
                    f"({'passed' if evidence.passed else 'failed'})"
                )
                # Phase markdown for test cohort evidence
                body = (
                    "# Test / command evidence\n\n"
                    f"- Task: `{task.id}`\n"
                    f"- Proposal: `{proposal.proposal_id}`\n"
                    f"- Exit code: `{evidence.exit_code}`\n"
                    f"- Passed: `{evidence.passed}`\n\n"
                    "## stdout\n\n```\n"
                    f"{evidence.stdout or '(empty)'}\n"
                    "```\n"
                )
                next_idx = _write_phase(ctx, state, "test", body)
                if not evidence.passed:
                    task.status = "failed"
                    task.error = f"Command failed exit={evidence.exit_code}"
                    return {
                        "tasks": _dump_tasks(tasks),
                        "cohort_queue": queue,
                        "current_task_id": task_id,
                        "pending_command": None,
                        "test_results": test_results,
                        "next_phase_index": next_idx,
                        "last_failure": {
                            "task_id": task.id,
                            "error": task.error,
                        },
                        "phase": "execute",
                        "written_paths": written,
                    }
                state = {**state, "next_phase_index": next_idx}  # type: ignore[typeddict-item]
            elif agent in {"documentation", "docs"}:
                docs_paths = ctx.docs.write_stub(
                    workspace=ctx.workspace,
                    task=task,
                    context=ctx.codegen_ctx(
                        task, design_note=str(state.get("design_note") or "")
                    ),
                )
                written.extend(docs_paths)
                finish_detail = (
                    f"wrote {len(docs_paths)} doc file(s): "
                    + (", ".join(docs_paths) if docs_paths else "(none)")
                )
            else:
                # Unknown agent → treat as developer write
                result = ctx.developer.apply_task(workspace=ctx.workspace, task=task)
                written.extend(result.written_paths)
                finish_detail = (
                    result.summary
                    or f"wrote {len(result.written_paths)} file(s) via developer fallback"
                )

            task.status = "completed"
            task.error = None
            task.updated_at = utc_now()
            ctx.events.append(
                "task_finish",
                message=(
                    f"Completed {task.id} “{task.name}”"
                    + (f" — {finish_detail}" if finish_detail else "")
                ),
                task_id=task.id,
                details={"agent": agent},
            )
            updates: dict[str, Any] = {
                "tasks": _dump_tasks(tasks),
                "cohort_queue": queue,
                "current_task_id": task_id,
                "pending_command": pending_command,
                "pending_destructive": pending_destructive,
                "test_results": test_results,
                "written_paths": written,
                "last_failure": None,
                "phase": "execute",
            }
            if agent in {"testing", "test"}:
                updates["next_phase_index"] = state.get("next_phase_index")
            return updates
        except GraphBubbleUp:
            # LangGraph interrupt / command bubble — must not be treated as task failure.
            raise
        except Exception as exc:  # noqa: BLE001 — task failure feeds Failure Analysis
            category = None
            error_text = str(exc)
            if isinstance(exc, ClassifiedLLMError):
                category = exc.category.value
                error_text = format_classified_message(error_text, exc.category)
            task.status = "failed"
            task.error = error_text
            task.updated_at = utc_now()
            ctx.events.append(
                "task_failed",
                message=(
                    f"Failed {task.id} “{task.name}” via {agent} agent: {error_text}"
                ),
                task_id=task.id,
                details={
                    "agent": agent,
                    "retry_count": task.retry_count,
                    "failure_category": category,
                },
            )
            return {
                "tasks": _dump_tasks(tasks),
                "cohort_queue": queue,
                "current_task_id": task_id,
                "last_failure": {
                    "task_id": task.id,
                    "error": error_text,
                    "failure_category": category,
                },
                "phase": "execute",
            }

    return execute_node


def make_sync_node(ctx: ExecutionContext) -> Callable[[ExecutionGraphState], dict]:
    def sync_node(state: ExecutionGraphState) -> dict[str, Any]:
        cohort = list(state.get("current_cohort") or [])
        tasks = _tasks_from_state(state)
        cohort_index = int(state.get("cohort_index") or 0)
        lines = [
            f"# Sync cohort {cohort_index}",
            "",
            f"- Workflow: `{state.get('workflow_id')}`",
            f"- Cohort tasks: {', '.join(f'`{t}`' for t in cohort) or '(none)'}",
            "",
            "## Task statuses",
            "",
        ]
        for task in tasks:
            if task.id in cohort:
                lines.append(f"- `{task.id}` → `{task.status}`")
        lines.append("")
        body = "\n".join(lines)
        next_idx = _write_phase(ctx, state, f"cohort_{cohort_index}", body)
        ctx.events.append(
            "cohort_synced",
            message=f"Synced cohort {cohort_index}",
            details={"cohort_ids": cohort},
        )

        completed = {t.id for t in tasks if t.status == "completed"}
        all_done = bool(tasks) and len(completed) == len(tasks)
        return {
            "phase": "sync",
            "next_phase_index": next_idx,
            "cohort_index": cohort_index + 1,
            "current_cohort": [],
            "cohort_queue": [],
            "completed": all_done,
        }

    return sync_node


def make_fail_analyze_node(
    ctx: ExecutionContext,
) -> Callable[[ExecutionGraphState], dict]:
    def fail_analyze_node(state: ExecutionGraphState) -> dict[str, Any]:
        last = state.get("last_failure") or {}
        task_id = last.get("task_id")
        error = str(last.get("error") or "unknown")
        tasks = _tasks_from_state(state)
        by_id = {t.id: t for t in tasks}
        if not task_id or task_id not in by_id:
            body = f"# Failure analysis\n\nMissing failure context: {last}\n"
            next_idx = _write_phase(ctx, state, "fail_analyze", body)
            return {
                "safe_stopped": True,
                "stop_reason": "Failure analysis missing task context",
                "next_phase_index": next_idx,
                "phase": "fail_analyze",
            }

        task = by_id[task_id]
        cap = get_settings().max_task_retries
        prefer_replan = task_id in (state.get("force_replan_task_ids") or [])
        failure_category = last.get("failure_category")
        # Enforce settings cap regardless of per-task max_retries from LLM.
        result = ctx.failure.analyze(
            task=task,
            error=error,
            max_retries=cap,
            prefer_replan=prefer_replan,
            failure_category=failure_category,
        )
        category_value = (
            result.failure_category.value if result.failure_category else None
        )
        body = (
            "# Failure analysis\n\n"
            f"- Task: `{task.id}`\n"
            f"- Error: {error}\n"
            f"- Category: `{category_value or 'unknown'}`\n"
            f"- Retry count: `{task.retry_count}`\n"
            f"- Cap: `{cap}`\n"
            f"- Recommendation: `{result.recommendation}`\n"
            f"- Reason: {result.reason}\n"
            f"- Prefer replan: `{prefer_replan}`\n"
        )
        next_idx = _write_phase(ctx, state, "fail_analyze", body)
        ctx.events.append(
            "fail_analyzed",
            message=(
                f"Failure analysis for {task.id}: recommend {result.recommendation} — "
                f"{result.reason}"
            ),
            task_id=task.id,
            details={
                "recommendation": result.recommendation,
                "failure_category": category_value,
            },
        )

        if result.recommendation == "retry" and task.retry_count < cap:
            task.retry_count += 1
            task.status = "pending"
            task.error = None
            task.updated_at = utc_now()
            ctx.events.append(
                "retry",
                message=(
                    f"Retrying {task.id} “{task.name}” "
                    f"(attempt {task.retry_count}/{cap}) after: {error}"
                ),
                task_id=task.id,
            )
            return {
                "tasks": _dump_tasks(tasks),
                "failure_recommendation": "retry",
                "last_failure": None,
                "cohort_queue": [],
                "current_cohort": [],
                "next_phase_index": next_idx,
                "phase": "fail_analyze",
                "safe_stopped": False,
            }

        if result.recommendation == "replan":
            patched, summary = apply_material_plan_patch(
                tasks,
                failed_task_id=task.id,
                note=str(result.plan_patch.get("note") or result.reason),
            )
            ctx.events.append(
                "replan",
                message=result.reason,
                task_id=task.id,
                details=summary,
            )
            replan_body = (
                "# Replan (material)\n\n"
                f"- Failed task: `{task.id}`\n"
                f"- Invalidated: {', '.join(summary.get('invalidated_task_ids') or [])}\n"
                f"- Note: {summary.get('note')}\n"
                "\nAwaiting plan re-approval via existing plan gate.\n"
            )
            next_idx = _write_phase(ctx, state, "replan", replan_body)
            return {
                "tasks": _dump_tasks(patched),
                "failure_recommendation": "replan",
                "plan_patch": summary,
                "awaiting_plan_reapproval": True,
                "last_failure": None,
                "cohort_queue": [],
                "current_cohort": [],
                "next_phase_index": next_idx,
                "phase": "replan",
                "safe_stopped": False,
                "completed": False,
            }

        task.status = "failed"
        return {
            "tasks": _dump_tasks(tasks),
            "failure_recommendation": "stop",
            "safe_stopped": True,
            "stop_reason": result.reason,
            "next_phase_index": next_idx,
            "phase": "fail_analyze",
        }

    return fail_analyze_node


def make_docs_stub_node(ctx: ExecutionContext) -> Callable[[ExecutionGraphState], dict]:
    """Success-path docs + report; parks for release approval (not terminal complete)."""

    def docs_stub_node(state: ExecutionGraphState) -> dict[str, Any]:
        notes_paths = ctx.docs.write_product_notes(
            workspace=ctx.workspace,
            plan=ctx.plan,
            design_note=str(state.get("design_note") or ""),
            specification=ctx.specification,
        )
        notes_display = ", ".join(f"`{p}`" for p in notes_paths) or "(none)"
        # Persist plan task statuses onto ctx.plan for the report builder via workspace
        # artifacts; full report is also written by CLI `report` and release finalize.
        artifact = ".agentic/artifacts/docs_complete.md"
        ctx.workspace.write_text(
            artifact,
            "# Documentation (Phase 5)\n\n"
            f"- Product notes: {notes_display}\n"
            "- Awaiting release approval before terminal complete.\n",
        )
        body = (
            "# Docs / pre-release\n\n"
            f"- Workflow: `{state.get('workflow_id')}`\n"
            f"- Notes: {notes_display}\n"
            "- Status: awaiting_release_approval\n"
        )
        next_idx = _write_phase(ctx, state, "docs", body)
        ctx.events.append(
            "docs_written",
            message="Documentation notes written; awaiting release approval",
            details={"notes": notes_paths},
        )
        return {
            "completed": False,
            "awaiting_release": True,
            "phase": "docs",
            "next_phase_index": next_idx,
            "written_paths": list(state.get("written_paths") or [])
            + list(notes_paths)
            + [artifact],
        }

    return docs_stub_node


def make_replan_park_node(ctx: ExecutionContext) -> Callable[[ExecutionGraphState], dict]:
    def replan_park_node(state: ExecutionGraphState) -> dict[str, Any]:
        # Terminal park for plan re-approval (handled outside the graph).
        _ = ctx
        return {
            "awaiting_plan_reapproval": True,
            "phase": "replan",
            "completed": False,
            "safe_stopped": False,
        }

    return replan_park_node


def make_safe_stop_node(ctx: ExecutionContext) -> Callable[[ExecutionGraphState], dict]:
    def safe_stop_node(state: ExecutionGraphState) -> dict[str, Any]:
        reason = state.get("stop_reason") or "Safe-stop"
        body = (
            "# Safe-stop\n\n"
            f"- Workflow: `{state.get('workflow_id')}`\n"
            f"- Reason: {reason}\n"
        )
        next_idx = _write_phase(ctx, state, "safe_stop", body)
        ctx.events.append(
            "safe_stop",
            message=f"Safe-stop: {reason}",
        )
        return {
            "safe_stopped": True,
            "stop_reason": reason,
            "phase": "safe_stop",
            "next_phase_index": next_idx,
        }

    return safe_stop_node


def make_complete_node(ctx: ExecutionContext) -> Callable[[ExecutionGraphState], dict]:
    def complete_node(state: ExecutionGraphState) -> dict[str, Any]:
        if state.get("phase") == "complete":
            return {"completed": True, "phase": "complete"}
        return make_docs_stub_node(ctx)(state)

    return complete_node
