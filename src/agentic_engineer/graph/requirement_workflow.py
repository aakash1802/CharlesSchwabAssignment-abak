"""Persisted workflow for CLI (analyze → clarify → spec → plan → approve)."""

from __future__ import annotations

import uuid
from pathlib import Path

from agentic_engineer.agents.task_planner import TaskPlanner
from agentic_engineer.governance.approvals import ApprovalError, ApprovalService
from agentic_engineer.graph.dependency import (
    parallel_cohorts,
    ready_tasks,
    render_ascii,
    render_mermaid,
    validate_graph,
)
from agentic_engineer.graph.nodes_requirement import (
    route_after_analysis,
    run_analyze,
    run_generate_spec,
)
from agentic_engineer.llm.base import LLMError, LLMProvider
from agentic_engineer.llm.factory import build_provider
from agentic_engineer.models.approval import ApprovalDecision, ApprovalType
from agentic_engineer.models.common import AgenticProjectConfig, utc_now
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.requirements import ClarificationAnswer
from agentic_engineer.models.workflow import RequirementWorkflowState
from agentic_engineer.persistence.json_store import JsonStore
from agentic_engineer.persistence.plan_store import PlanStore
from agentic_engineer.persistence.readable_store import ReadableArtifactStore
from agentic_engineer.persistence.spec_store import SpecStore
from agentic_engineer.persistence.workflow_store import WorkflowStore
from agentic_engineer.workspace.workspace import Workspace

class WorkflowError(Exception):
    """Invalid workflow transition or missing state."""


class RequirementWorkflowService:
    def __init__(
        self,
        workspace: Workspace,
        *,
        provider: LLMProvider | None = None,
    ) -> None:
        self.workspace = workspace
        self.provider = provider or build_provider()
        self.workflows = WorkflowStore(workspace.agentic_dir)
        self.specs = SpecStore(workspace.agentic_dir)
        self.plans = PlanStore(workspace.agentic_dir)
        self.readable = ReadableArtifactStore(workspace.agentic_dir)

    def _config_store(self) -> JsonStore:
        return JsonStore(self.workspace.agentic_dir)

    def _save_config(self, **updates: object) -> AgenticProjectConfig:
        store = self._config_store()
        config = store.read_model("config.json", AgenticProjectConfig)
        data = config.model_dump(mode="json")
        data.update(updates)
        data["updated_at"] = utc_now()
        config = AgenticProjectConfig.model_validate(data)
        store.write_model("config.json", config)
        return config

    def _approvals(self, workflow_id: str) -> ApprovalService:
        return ApprovalService(self.workflows.workflow_dir(workflow_id))

    def load_active(self) -> RequirementWorkflowState:
        config = self.workspace.load_config()
        if not config.active_workflow_id:
            raise WorkflowError("No active workflow. Run `agentic run` first.")
        return self.workflows.load(config.active_workflow_id)

    def start(self, requirement: str) -> RequirementWorkflowState:
        text = requirement.strip()
        if not text:
            raise WorkflowError("Requirement must not be empty")

        workflow_id = f"workflow_{uuid.uuid4().hex[:12]}"
        state = RequirementWorkflowState(
            workflow_id=workflow_id,
            requirement=text,
            status="analyzing",
        )
        self.workflows.save(state)
        self._save_config(
            active_workflow_id=workflow_id,
            active_specification_id=None,
            active_plan_id=None,
        )

        analysis = run_analyze(text, self.provider)
        state.analysis = analysis
        self.readable.write_analysis(state, phase_name="analysis", phase_index=1)
        if route_after_analysis(analysis) == "await_clarification":
            state.status = "awaiting_clarification"
            self.workflows.save(state)
            self.readable.write_clarification(state, phase_index=2)
            return state

        return self._generate_and_request_approval(state)

    def provide_answers(self, answers: list[str]) -> RequirementWorkflowState:
        state = self.load_active()
        if state.status != "awaiting_clarification":
            raise WorkflowError(
                f"Workflow is not awaiting clarification (status={state.status})"
            )
        if state.analysis is None:
            raise WorkflowError("Missing analysis on workflow state")

        questions = [q for q in state.analysis.clarification_questions if q.essential]
        if not answers:
            raise WorkflowError("At least one clarification answer is required")
        if len(answers) < len(questions):
            raise WorkflowError(
                f"Expected {len(questions)} answer(s) for essential questions; got {len(answers)}"
            )

        paired: list[ClarificationAnswer] = []
        for idx, question in enumerate(questions):
            paired.append(
                ClarificationAnswer(question_id=question.id, answer=answers[idx].strip())
            )
        # Extra answers map to remaining non-essential questions if present.
        extras = [q for q in state.analysis.clarification_questions if not q.essential]
        for offset, question in enumerate(extras):
            ans_idx = len(questions) + offset
            if ans_idx < len(answers):
                paired.append(
                    ClarificationAnswer(
                        question_id=question.id, answer=answers[ans_idx].strip()
                    )
                )

        state.clarification_answers = paired
        # Clarifications resolve the gate; regenerate a tightened analysis snapshot.
        updated = state.analysis.model_copy(
            update={
                "needs_clarification": False,
                "assumptions": list(state.analysis.assumptions)
                + [f"Clarified {a.question_id}: {a.answer}" for a in paired],
            }
        )
        if not updated.functional_requirements:
            updated = updated.model_copy(
                update={
                    "functional_requirements": [a.answer for a in paired],
                    "summary": paired[0].answer if paired else updated.summary,
                }
            )
        state.analysis = updated
        self.readable.write_analysis(state, phase_name="analysis", phase_index=1)
        self.readable.write_clarification(state, phase_index=2)
        return self._generate_and_request_approval(state)

    def _generate_and_request_approval(
        self, state: RequirementWorkflowState
    ) -> RequirementWorkflowState:
        assert state.analysis is not None
        state.status = "generating_spec"
        self.workflows.save(state)

        spec = run_generate_spec(
            workflow_id=state.workflow_id,
            analysis=state.analysis,
            answers=state.clarification_answers,
            provider=self.provider,
        )
        self.specs.save(spec)
        state.specification = spec
        state.specification_id = spec.id

        approval = self._approvals(state.workflow_id).create_pending(
            workflow_id=state.workflow_id,
            approval_type=ApprovalType.SPECIFICATION,
            requested_action="Approve generated specification for engineering planning",
            artifact_ref=spec.id,
        )
        state.pending_approval_id = approval.id
        state.status = "awaiting_spec_approval"
        self.workflows.save(state)
        self.readable.write_specification(state, phase_index=3)
        self._save_config(
            active_workflow_id=state.workflow_id,
            active_specification_id=spec.id,
        )
        return state

    def approve(self, *, comment: str | None = None) -> RequirementWorkflowState:
        return self._decide(ApprovalDecision.APPROVED, comment=comment)

    def reject(
        self,
        *,
        comment: str | None = None,
        changes_requested: bool = False,
    ) -> RequirementWorkflowState:
        decision = (
            ApprovalDecision.CHANGES_REQUESTED
            if changes_requested
            else ApprovalDecision.REJECTED
        )
        return self._decide(decision, comment=comment)

    def _decide(
        self,
        decision: ApprovalDecision,
        *,
        comment: str | None,
    ) -> RequirementWorkflowState:
        state = self.load_active()
        if state.status == "awaiting_spec_approval":
            return self._decide_specification(state, decision, comment=comment)
        if state.status == "awaiting_plan_approval":
            return self._decide_plan(state, decision, comment=comment)
        raise WorkflowError(
            f"No approval pending (status={state.status})"
        )

    def _decide_specification(
        self,
        state: RequirementWorkflowState,
        decision: ApprovalDecision,
        *,
        comment: str | None,
    ) -> RequirementWorkflowState:
        if not state.pending_approval_id:
            raise WorkflowError("Missing pending approval id")

        try:
            self._approvals(state.workflow_id).decide(
                state.pending_approval_id,
                decision,
                comment=comment,
            )
        except ApprovalError as exc:
            raise WorkflowError(str(exc)) from exc

        if decision == ApprovalDecision.APPROVED:
            state.status = "spec_approved"
            state.stop_reason = None
        elif decision == ApprovalDecision.CHANGES_REQUESTED:
            state.status = "stopped"
            state.stop_reason = "Specification changes requested"
        else:
            state.status = "spec_rejected"
            state.stop_reason = "Specification rejected"
        state.pending_approval_id = None
        self.workflows.save(state)
        self.readable.write_approval(
            state, decision, comment=comment, phase_index=4, phase_name="approval"
        )
        if state.specification is not None:
            self.readable.write_specification(state, phase_index=3)

        # Controlled autonomy: advance past generation/validation automatically;
        # park again only at the next human gate (plan approval).
        if decision == ApprovalDecision.APPROVED:
            return self.generate_plan()
        return state

    def _can_generate_plan(self, state: RequirementWorkflowState) -> bool:
        if state.specification is None:
            return False
        if state.status == "spec_approved":
            return True
        if state.status == "plan_rejected":
            return True
        if state.status == "stopped" and state.stop_reason == "Plan changes requested":
            return True
        return False

    def generate_plan(self) -> RequirementWorkflowState:
        """Generate a validated plan from the approved specification and request approval."""
        state = self.load_active()
        if not self._can_generate_plan(state):
            raise WorkflowError(
                "Plan generation requires an approved specification "
                f"(status={state.status}). Approve the spec first, then run `agentic plan`."
            )
        assert state.specification is not None

        state.status = "planning"
        state.stop_reason = None
        self.workflows.save(state)

        try:
            plan = TaskPlanner(self.provider).plan(
                workflow_id=state.workflow_id,
                specification=state.specification,
            )
        except LLMError as exc:
            state.status = "spec_approved"
            self.workflows.save(state)
            raise WorkflowError(str(exc)) from exc

        validation = validate_graph(plan.tasks)
        if not validation.ok:
            state.status = "spec_approved"
            self.workflows.save(state)
            detail = "; ".join(validation.error_messages)
            raise WorkflowError(f"Generated plan failed validation: {detail}")

        self.plans.save(plan)
        state.plan = plan
        state.plan_id = plan.id

        approval = self._approvals(state.workflow_id).create_pending(
            workflow_id=state.workflow_id,
            approval_type=ApprovalType.PLAN,
            requested_action="Approve engineering plan for execution",
            artifact_ref=plan.id,
        )
        state.pending_approval_id = approval.id
        state.status = "awaiting_plan_approval"
        self.workflows.save(state)
        self.readable.write_plan(state, phase_index=5)
        self._save_config(
            active_workflow_id=state.workflow_id,
            active_specification_id=state.specification_id,
            active_plan_id=plan.id,
        )
        return state

    def get_plan(self) -> EngineeringPlan:
        state = self.load_active()
        if state.plan is not None:
            return state.plan
        if state.plan_id:
            return self.plans.load(state.plan_id)
        config = self.workspace.load_config()
        if config.active_plan_id:
            return self.plans.load(config.active_plan_id)
        raise WorkflowError("No plan generated yet. Run `agentic plan` after spec approval.")

    def plan_or_show(self, *, generate: bool = False) -> RequirementWorkflowState:
        """Generate a new plan when appropriate; otherwise return state with existing plan."""
        state = self.load_active()
        if generate:
            if not self._can_generate_plan(state):
                raise WorkflowError(
                    "Cannot regenerate plan in the current state "
                    f"(status={state.status})"
                )
            return self.generate_plan()
        if self._can_generate_plan(state):
            return self.generate_plan()
        if state.plan is None and state.plan_id:
            state.plan = self.plans.load(state.plan_id)
        if state.plan is None:
            raise WorkflowError(
                "No plan available. Approve the specification, then run `agentic plan`."
            )
        return state

    def _decide_plan(
        self,
        state: RequirementWorkflowState,
        decision: ApprovalDecision,
        *,
        comment: str | None,
    ) -> RequirementWorkflowState:
        if not state.pending_approval_id:
            raise WorkflowError("Missing pending approval id")

        try:
            self._approvals(state.workflow_id).decide(
                state.pending_approval_id,
                decision,
                comment=comment,
            )
        except ApprovalError as exc:
            raise WorkflowError(str(exc)) from exc

        if decision == ApprovalDecision.APPROVED:
            state.status = "plan_approved"
            state.stop_reason = None
        elif decision == ApprovalDecision.CHANGES_REQUESTED:
            state.status = "stopped"
            state.stop_reason = "Plan changes requested"
        else:
            state.status = "plan_rejected"
            state.stop_reason = "Plan rejected"
        state.pending_approval_id = None
        self.workflows.save(state)
        self.readable.write_approval(
            state,
            decision,
            comment=comment,
            phase_index=6,
            phase_name="plan_approval",
        )
        if state.plan is not None:
            self.readable.write_plan(state, phase_index=5)
        return state

    def format_plan_display(self, plan: EngineeringPlan) -> str:
        ready = ready_tasks(plan.tasks, completed_ids=set())
        cohorts = parallel_cohorts(plan.tasks)
        lines = [
            f"plan_id: {plan.id}",
            f"specification_id: {plan.specification_id}",
            f"summary: {plan.summary}",
            "",
            "tasks:",
            render_ascii(plan.tasks),
            "",
            "mermaid:",
            render_mermaid(plan.tasks),
            "",
            "ready:",
        ]
        if not ready:
            lines.append("  (none)")
        else:
            for task in ready:
                lines.append(f"  - {task.id}: {task.name}")
        lines.append("parallel_cohorts:")
        for idx, cohort in enumerate(cohorts):
            ids = ", ".join(t.id for t in cohort)
            lines.append(f"  - cohort_{idx}: {ids}")
        return "\n".join(lines)

    def current_spec_path(self) -> Path | None:
        config = self.workspace.load_config()
        if not config.active_specification_id:
            return None
        return self.workspace.agentic_dir / "specifications" / f"{config.active_specification_id}.json"

    def readable_root(self) -> Path:
        return self.readable.root
