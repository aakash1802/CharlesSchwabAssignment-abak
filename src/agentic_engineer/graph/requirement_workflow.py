"""Persisted requirement workflow for CLI (analyze → clarify → spec → approve)."""

from __future__ import annotations

import uuid
from pathlib import Path

from agentic_engineer.governance.approvals import ApprovalError, ApprovalService
from agentic_engineer.graph.nodes_requirement import (
    route_after_analysis,
    run_analyze,
    run_generate_spec,
)
from agentic_engineer.llm.base import LLMProvider
from agentic_engineer.llm.factory import build_provider
from agentic_engineer.models.approval import ApprovalDecision, ApprovalType
from agentic_engineer.models.common import AgenticProjectConfig, utc_now
from agentic_engineer.models.requirements import ClarificationAnswer
from agentic_engineer.models.workflow import RequirementWorkflowState
from agentic_engineer.persistence.json_store import JsonStore
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
        self._save_config(active_workflow_id=workflow_id, active_specification_id=None)

        analysis = run_analyze(text, self.provider)
        state.analysis = analysis
        if route_after_analysis(analysis) == "await_clarification":
            state.status = "awaiting_clarification"
            self.workflows.save(state)
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
        if state.status != "awaiting_spec_approval":
            raise WorkflowError(
                f"No specification pending approval (status={state.status})"
            )
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
        return state

    def current_spec_path(self) -> Path | None:
        config = self.workspace.load_config()
        if not config.active_specification_id:
            return None
        return self.workspace.agentic_dir / "specifications" / f"{config.active_specification_id}.json"
