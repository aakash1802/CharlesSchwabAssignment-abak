"""Phase 4 execution service — LangGraph orchestration + JSON mirror."""

from __future__ import annotations

from typing import Any

from langgraph.types import Command

from agentic_engineer.execution.events import EventSink, ExecutionEventLog
from agentic_engineer.execution.progress import echo_progress
from agentic_engineer.governance.approvals import ApprovalError, ApprovalService
from agentic_engineer.graph.builder import build_execution_graph, open_checkpointer
from agentic_engineer.graph.nodes_execution import ExecutionContext
from agentic_engineer.graph.state import ExecutionGraphState
from agentic_engineer.llm.base import LLMProvider
from agentic_engineer.llm.factory import build_provider
from agentic_engineer.models.approval import ApprovalDecision, ApprovalType
from agentic_engineer.models.execution import CommandProposal, DestructiveProposal
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.specification import Specification
from agentic_engineer.models.task import Task
from agentic_engineer.models.workflow import RequirementWorkflowState
from agentic_engineer.persistence.readable_store import ReadableArtifactStore
from agentic_engineer.persistence.spec_store import SpecStore
from agentic_engineer.persistence.workflow_store import WorkflowStore
from agentic_engineer.workspace.workspace import Workspace


class ExecutionError(Exception):
    """Invalid execution transition or missing plan."""


class ExecutionWorkflowService:
    """Drive approved-plan → execute with checkpointer resume."""

    def __init__(
        self,
        workspace: Workspace,
        *,
        provider: LLMProvider | None = None,
        workflows: WorkflowStore | None = None,
        on_execution_event: EventSink | None = echo_progress,
    ) -> None:
        self.workspace = workspace
        self.provider = provider or build_provider()
        self.workflows = workflows or WorkflowStore(workspace.agentic_dir)
        self.readable = ReadableArtifactStore(workspace.agentic_dir)
        self.on_execution_event = on_execution_event
        self._conn: Any | None = None

    def _approvals(self, workflow_id: str) -> ApprovalService:
        return ApprovalService(self.workflows.workflow_dir(workflow_id))

    def _events(self, workflow_id: str) -> ExecutionEventLog:
        return ExecutionEventLog(
            self.workflows.workflow_dir(workflow_id),
            on_event=self.on_execution_event,
        )

    def _load_specification(
        self, state: RequirementWorkflowState, plan: EngineeringPlan
    ) -> Specification | None:
        if state.specification is not None:
            return state.specification
        spec_id = state.specification_id or plan.specification_id
        if not spec_id:
            return None
        try:
            return SpecStore(self.workspace.agentic_dir).load(spec_id)
        except Exception:  # noqa: BLE001 — missing/corrupt spec must not block execute
            return None

    def _compile(self, state: RequirementWorkflowState, plan: EngineeringPlan):
        workflow_dir = self.workflows.workflow_dir(state.workflow_id)
        checkpointer, conn = open_checkpointer(workflow_dir)
        self._conn = conn
        ctx = ExecutionContext(
            workspace=self.workspace,
            provider=self.provider,
            plan=plan,
            events=self._events(state.workflow_id),
            readable=self.readable,
            specification=self._load_specification(state, plan),
            workflow_dir=workflow_dir,
        )
        graph = build_execution_graph(ctx)
        return graph.compile(checkpointer=checkpointer), ctx

    def _thread_config(self, thread_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}}

    def _mirror_from_graph(
        self,
        app_state: RequirementWorkflowState,
        values: dict[str, Any],
        *,
        interrupted: dict[str, Any] | None = None,
    ) -> RequirementWorkflowState:
        tasks_raw = values.get("tasks")
        if tasks_raw and app_state.plan is not None:
            tasks = [Task.model_validate(item) for item in tasks_raw]
            app_state.plan = app_state.plan.model_copy(update={"tasks": tasks})

        app_state.design_note = values.get("design_note") or app_state.design_note
        app_state.current_cohort_ids = list(values.get("current_cohort") or [])
        app_state.cohort_index = int(values.get("cohort_index") or app_state.cohort_index)
        app_state.next_phase_index = int(
            values.get("next_phase_index") or app_state.next_phase_index
        )
        if values.get("test_results") is not None:
            from agentic_engineer.models.execution import CommandEvidence

            app_state.test_results = [
                CommandEvidence.model_validate(item) for item in values["test_results"]
            ]

        if interrupted:
            kind = interrupted.get("type")
            proposal_data = interrupted.get("proposal") or {}
            if kind == "command":
                proposal = CommandProposal.model_validate(proposal_data)
                app_state.pending_command = proposal
                app_state.pending_destructive = None
                approval = self._approvals(app_state.workflow_id).create_pending(
                    workflow_id=app_state.workflow_id,
                    approval_type=ApprovalType.COMMAND,
                    requested_action=self._format_command_action(proposal),
                    artifact_ref=proposal.proposal_id,
                )
                app_state.pending_approval_id = approval.id
                app_state.status = "awaiting_command_approval"
            elif kind == "destructive":
                proposal_d = DestructiveProposal.model_validate(proposal_data)
                app_state.pending_destructive = proposal_d
                app_state.pending_command = None
                approval = self._approvals(app_state.workflow_id).create_pending(
                    workflow_id=app_state.workflow_id,
                    approval_type=ApprovalType.DESTRUCTIVE,
                    requested_action=(
                        f"{proposal_d.action}: {', '.join(proposal_d.paths)}"
                    ),
                    artifact_ref=proposal_d.proposal_id,
                )
                app_state.pending_approval_id = approval.id
                app_state.status = "awaiting_destructive_approval"
        elif values.get("awaiting_plan_reapproval"):
            # Material replan — park on existing plan gate UX.
            if app_state.plan is not None and values.get("tasks"):
                tasks = [Task.model_validate(item) for item in values["tasks"]]
                app_state.plan = app_state.plan.model_copy(update={"tasks": tasks})
                from agentic_engineer.persistence.plan_store import PlanStore

                PlanStore(self.workspace.agentic_dir).save(app_state.plan)
            app_state.plan_patch = values.get("plan_patch") or app_state.plan_patch
            approval = self._approvals(app_state.workflow_id).create_pending(
                workflow_id=app_state.workflow_id,
                approval_type=ApprovalType.PLAN,
                requested_action="Approve material replan patch for continued execution",
                artifact_ref=app_state.plan_id,
            )
            app_state.pending_approval_id = approval.id
            app_state.status = "awaiting_plan_approval"
            app_state.pending_command = None
            app_state.pending_destructive = None
            self.readable.write_plan(app_state, phase_index=app_state.next_phase_index)
        elif values.get("awaiting_release"):
            from agentic_engineer.reporting.report import ReportBuilder

            ReportBuilder(self.workspace.agentic_dir).write(app_state)
            approval = self._approvals(app_state.workflow_id).create_pending(
                workflow_id=app_state.workflow_id,
                approval_type=ApprovalType.RELEASE,
                requested_action="Approve release / mark workflow complete",
                artifact_ref=app_state.workflow_id,
            )
            app_state.pending_approval_id = approval.id
            app_state.status = "awaiting_release_approval"
            app_state.stop_reason = None
            app_state.pending_command = None
            app_state.pending_destructive = None
        elif values.get("safe_stopped"):
            app_state.status = "safe_stopped"
            app_state.stop_reason = values.get("stop_reason") or app_state.stop_reason
            app_state.pending_approval_id = None
            app_state.pending_command = None
            app_state.pending_destructive = None
            from agentic_engineer.reporting.report import ReportBuilder

            ReportBuilder(self.workspace.agentic_dir).write(app_state)
        elif values.get("completed"):
            app_state.status = "completed"
            app_state.stop_reason = None
            app_state.pending_approval_id = None
            app_state.pending_command = None
            app_state.pending_destructive = None
        else:
            app_state.status = "executing"
            app_state.pending_command = None
            app_state.pending_destructive = None

        self.workflows.save(app_state)
        return app_state

    @staticmethod
    def _format_command_action(proposal: CommandProposal) -> str:
        if proposal.kind == "shell":
            cmd = proposal.shell or ""
        else:
            cmd = " ".join(proposal.argv)
        reason = f" — {proposal.reason}" if proposal.reason else ""
        return f"Run command: {cmd}{reason}"

    def _extract_interrupt(self, result: Any) -> dict[str, Any] | None:
        if not isinstance(result, dict):
            return None
        interrupts = result.get("__interrupt__")
        if not interrupts:
            return None
        first = interrupts[0]
        value = getattr(first, "value", first)
        return value if isinstance(value, dict) else {"raw": value}

    def start_or_resume(
        self,
        state: RequirementWorkflowState,
        *,
        force_fail_task_ids: list[str] | None = None,
        force_destructive_task_ids: list[str] | None = None,
        force_replan_task_ids: list[str] | None = None,
    ) -> RequirementWorkflowState:
        if state.plan is None:
            raise ExecutionError("Cannot execute without an approved plan")
        if state.status not in {
            "plan_approved",
            "executing",
            "awaiting_command_approval",
            "awaiting_destructive_approval",
            "awaiting_release_approval",
            "safe_stopped",
        }:
            raise ExecutionError(
                f"Execution not allowed from status={state.status}"
            )

        thread_id = state.execution_thread_id or state.workflow_id
        state.execution_thread_id = thread_id
        if force_fail_task_ids:
            state.force_fail_task_ids = list(force_fail_task_ids)
        if force_replan_task_ids:
            state.force_replan_task_ids = list(force_replan_task_ids)

        app, _ctx = self._compile(state, state.plan)
        config = self._thread_config(thread_id)
        snap = app.get_state(config)

        if snap.values and snap.next:
            # Already mid-flight (e.g. parked interrupt) — do not re-invoke without resume.
            if state.status in {
                "awaiting_command_approval",
                "awaiting_destructive_approval",
                "awaiting_release_approval",
            }:
                return state
            # Resume after process kill mid-node without interrupt payload.
            result = app.invoke(None, config)
        elif snap.values and not snap.next:
            # Terminal checkpoint already present — re-mirror (release/replan park).
            if state.status == "awaiting_release_approval":
                return state
            return self._mirror_from_graph(state, dict(snap.values))
        else:
            initial: ExecutionGraphState = {
                "workflow_id": state.workflow_id,
                "thread_id": thread_id,
                "plan_id": state.plan_id or state.plan.id,
                "tasks": [t.model_dump(mode="json") for t in state.plan.tasks],
                "design_note": state.design_note or "",
                "current_cohort": [],
                "cohort_queue": [],
                "cohort_index": 0,
                "test_results": [],
                "errors": [],
                "phase": "start",
                "next_phase_index": state.next_phase_index or 7,
                "force_fail_task_ids": list(
                    force_fail_task_ids or state.force_fail_task_ids or []
                ),
                "force_destructive_task_ids": list(force_destructive_task_ids or []),
                "force_replan_task_ids": list(
                    force_replan_task_ids or state.force_replan_task_ids or []
                ),
                "awaiting_plan_reapproval": False,
                "awaiting_release": False,
                "plan_patch": None,
                "completed": False,
                "safe_stopped": False,
                "written_paths": [],
            }
            state.status = "executing"
            self.workflows.save(state)
            result = app.invoke(initial, config)

        interrupted = self._extract_interrupt(result)
        values = dict(result) if isinstance(result, dict) else {}
        # Prefer checkpoint values (cleaner than interrupt wrapper keys).
        snap = app.get_state(config)
        if snap.values:
            values = dict(snap.values)
        return self._mirror_from_graph(state, values, interrupted=interrupted)

    def resume_after_decision(
        self,
        state: RequirementWorkflowState,
        *,
        approved: bool,
        comment: str | None = None,
    ) -> RequirementWorkflowState:
        if state.status not in {
            "awaiting_command_approval",
            "awaiting_destructive_approval",
        }:
            raise ExecutionError(
                f"No execution approval pending (status={state.status})"
            )
        if not state.pending_approval_id:
            raise ExecutionError("Missing pending approval id")
        if not state.execution_thread_id:
            raise ExecutionError("Missing execution thread id")

        decision = (
            ApprovalDecision.APPROVED if approved else ApprovalDecision.REJECTED
        )
        try:
            self._approvals(state.workflow_id).decide(
                state.pending_approval_id,
                decision,
                comment=comment,
            )
        except ApprovalError as exc:
            raise ExecutionError(str(exc)) from exc

        app, _ctx = self._compile(state, state.plan)  # type: ignore[arg-type]
        config = self._thread_config(state.execution_thread_id)
        result = app.invoke(
            Command(resume={"approved": approved, "comment": comment}),
            config,
        )
        interrupted = self._extract_interrupt(result)
        snap = app.get_state(config)
        values = dict(snap.values) if snap.values else dict(result)
        state.pending_approval_id = None
        state.pending_command = None
        state.pending_destructive = None
        return self._mirror_from_graph(state, values, interrupted=interrupted)

    def finalize_release(
        self,
        state: RequirementWorkflowState,
        *,
        approved: bool,
        comment: str | None = None,
    ) -> RequirementWorkflowState:
        if state.status != "awaiting_release_approval":
            raise ExecutionError(
                f"No release approval pending (status={state.status})"
            )
        if not state.pending_approval_id:
            raise ExecutionError("Missing pending approval id")
        decision = (
            ApprovalDecision.APPROVED if approved else ApprovalDecision.REJECTED
        )
        try:
            self._approvals(state.workflow_id).decide(
                state.pending_approval_id,
                decision,
                comment=comment,
            )
        except ApprovalError as exc:
            raise ExecutionError(str(exc)) from exc

        events = self._events(state.workflow_id)
        if approved:
            events.append("completed", message="Release approved; workflow complete")
            state.status = "completed"
            state.stop_reason = None
        else:
            events.append(
                "safe_stop",
                message=f"Release rejected: {comment or 'no comment'}",
            )
            state.status = "safe_stopped"
            state.stop_reason = "Release rejected"
        state.pending_approval_id = None
        from agentic_engineer.reporting.report import ReportBuilder

        ReportBuilder(self.workspace.agentic_dir).write(state)
        self.workflows.save(state)
        return state

    def continue_after_replan_approval(
        self, state: RequirementWorkflowState
    ) -> RequirementWorkflowState:
        """After material replan is approved, resume execution from patched tasks."""
        if state.plan is None:
            raise ExecutionError("Cannot continue replan without a plan")
        # Clear force-fail so the retried path can succeed after replan in demos/tests
        # unless caller re-sets them. Keep force_replan cleared for this task.
        state.force_fail_task_ids = []
        state.force_replan_task_ids = []
        state.plan_patch = None
        state.status = "plan_approved"
        # New thread segment so invoke starts a fresh run with patched tasks.
        state.execution_thread_id = f"{state.workflow_id}_replan_{state.cohort_index}"
        self.workflows.save(state)
        return self.start_or_resume(state)

    def pending_interrupt_payload(
        self, state: RequirementWorkflowState
    ) -> dict[str, Any] | None:
        if not state.execution_thread_id or state.plan is None:
            return None
        app, _ = self._compile(state, state.plan)
        snap = app.get_state(self._thread_config(state.execution_thread_id))
        if not snap.tasks:
            return None
        # Interrupts are exposed via get_state interrupts in newer LG; fall back to mirror.
        if state.pending_command is not None:
            return {
                "type": "command",
                "proposal": state.pending_command.model_dump(mode="json"),
            }
        if state.pending_destructive is not None:
            return {
                "type": "destructive",
                "proposal": state.pending_destructive.model_dump(mode="json"),
            }
        return None
