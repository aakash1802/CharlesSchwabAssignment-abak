"""Human-readable Markdown artifacts under `.agentic/readable/` (R13)."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.graph.dependency import (
    parallel_cohorts,
    ready_tasks,
    render_ascii,
    render_mermaid,
)
from agentic_engineer.models.approval import ApprovalDecision
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.requirements import ClarificationAnswer, RequirementAnalysis
from agentic_engineer.models.specification import Specification
from agentic_engineer.models.workflow import RequirementWorkflowState


def _bullet_section(title: str, items: list[str]) -> str:
    lines = [f"## {title}", ""]
    if not items:
        lines.append("_None_")
    else:
        lines.extend(f"- {item}" for item in items)
    lines.append("")
    return "\n".join(lines)


class ReadableArtifactStore:
    """Writes Markdown review copies derived from workflow JSON state."""

    def __init__(self, agentic_dir: Path) -> None:
        self._root = agentic_dir / "readable"
        self._phases = self._root / "phases"
        self._root.mkdir(parents=True, exist_ok=True)
        self._phases.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def write_analysis(
        self,
        state: RequirementWorkflowState,
        *,
        phase_name: str = "analysis",
        phase_index: int = 1,
    ) -> Path:
        analysis = state.analysis
        if analysis is None:
            raise ValueError("Cannot write analysis Markdown without analysis")
        body = self._render_analysis(state.workflow_id, state.status, analysis)
        latest = self._root / "ANALYSIS.md"
        latest.write_text(body, encoding="utf-8")
        phase_path = self._write_phase(phase_index, phase_name, body)
        return phase_path

    def write_clarification(
        self,
        state: RequirementWorkflowState,
        *,
        phase_index: int = 2,
    ) -> Path:
        analysis = state.analysis
        if analysis is None:
            raise ValueError("Cannot write clarification Markdown without analysis")
        lines = [
            "# Clarification",
            "",
            f"- Workflow: `{state.workflow_id}`",
            f"- Status: `{state.status}`",
            "",
            "## Questions awaiting answers",
            "",
        ]
        essential = [q for q in analysis.clarification_questions if q.essential]
        if not essential:
            lines.append("_None_")
        else:
            for question in essential:
                lines.append(f"- **[{question.id}]** {question.question}")
                lines.append(f"  - Reason: {question.reason}")
        lines.append("")
        if state.clarification_answers:
            lines.extend(["## Recorded answers", ""])
            for answer in state.clarification_answers:
                lines.append(f"- **{answer.question_id}:** {answer.answer}")
            lines.append("")
        body = "\n".join(lines)
        return self._write_phase(phase_index, "clarification", body)

    def write_specification(
        self,
        state: RequirementWorkflowState,
        *,
        phase_index: int = 3,
    ) -> Path:
        spec = state.specification
        if spec is None:
            raise ValueError("Cannot write specification Markdown without specification")
        body = self._render_specification(state.status, spec, state.clarification_answers)
        latest = self._root / "SPECIFICATION.md"
        latest.write_text(body, encoding="utf-8")
        companion = (
            self._root.parent / "specifications" / f"{spec.id}.md"
        )
        companion.parent.mkdir(parents=True, exist_ok=True)
        companion.write_text(body, encoding="utf-8")
        return self._write_phase(phase_index, "specification", body)

    def write_approval(
        self,
        state: RequirementWorkflowState,
        decision: ApprovalDecision,
        *,
        comment: str | None = None,
        phase_index: int = 4,
        phase_name: str = "approval",
    ) -> Path:
        lines = [
            "# Approval decision",
            "",
            f"- Workflow: `{state.workflow_id}`",
            f"- Status: `{state.status}`",
            f"- Decision: `{decision.value}`",
            f"- Specification: `{state.specification_id or '(none)'}`",
            f"- Plan: `{state.plan_id or '(none)'}`",
        ]
        if comment:
            lines.append(f"- Comment: {comment}")
        if state.stop_reason:
            lines.append(f"- Stop reason: {state.stop_reason}")
        see_also = [
            "",
            "See also:",
            "",
            "- [SPECIFICATION.md](../SPECIFICATION.md)",
            "- [ANALYSIS.md](../ANALYSIS.md)",
        ]
        if state.plan_id:
            see_also.append("- [PLAN.md](../PLAN.md)")
        see_also.append("")
        lines.extend(see_also)
        body = "\n".join(lines)
        return self._write_phase(phase_index, phase_name, body)

    def write_plan(
        self,
        state: RequirementWorkflowState,
        *,
        phase_index: int = 5,
    ) -> Path:
        plan = state.plan
        if plan is None:
            raise ValueError("Cannot write plan Markdown without plan")
        body = self._render_plan(state.status, plan)
        latest = self._root / "PLAN.md"
        latest.write_text(body, encoding="utf-8")
        companion = self._root.parent / "plans" / f"{plan.id}.md"
        companion.parent.mkdir(parents=True, exist_ok=True)
        companion.write_text(body, encoding="utf-8")
        return self._write_phase(phase_index, "plan", body)

    def write_execution_phase(
        self,
        name: str,
        body: str,
        *,
        phase_index: int,
    ) -> Path:
        """Write a Phase 4+ execution cohort summary under readable/phases/."""
        return self._write_phase(phase_index, name, body)

    def write_report(self, body: str) -> Path:
        """Write latest human-readable engineering report (Phase 5)."""
        path = self._root / "REPORT.md"
        path.write_text(body, encoding="utf-8")
        return path

    def _write_phase(self, index: int, name: str, body: str) -> Path:
        path = self._phases / f"{index:02d}_{name}.md"
        path.write_text(body, encoding="utf-8")
        return path

    @staticmethod
    def _render_analysis(
        workflow_id: str,
        status: str,
        analysis: RequirementAnalysis,
    ) -> str:
        lines = [
            "# Requirement analysis",
            "",
            f"- Workflow: `{workflow_id}`",
            f"- Status: `{status}`",
            f"- Needs clarification: `{analysis.needs_clarification}`",
            "",
            "## Original requirement",
            "",
            analysis.original_requirement.strip(),
            "",
            "## Summary",
            "",
            analysis.summary.strip() or "_Empty_",
            "",
            _bullet_section("Functional requirements", analysis.functional_requirements),
            _bullet_section(
                "Non-functional requirements", analysis.non_functional_requirements
            ),
            _bullet_section("Constraints", analysis.constraints),
            _bullet_section("Ambiguities", analysis.ambiguities),
            _bullet_section("Missing information", analysis.missing_information),
            _bullet_section("Assumptions", analysis.assumptions),
        ]
        lines.extend(["## Clarification questions", ""])
        if not analysis.clarification_questions:
            lines.append("_None_")
        else:
            for question in analysis.clarification_questions:
                essential = "essential" if question.essential else "optional"
                lines.append(
                    f"- **[{question.id}]** ({essential}) {question.question}"
                )
                lines.append(f"  - Reason: {question.reason}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _render_specification(
        status: str,
        spec: Specification,
        answers: list[ClarificationAnswer],
    ) -> str:
        lines = [
            f"# {spec.title}",
            "",
            f"- Specification id: `{spec.id}`",
            f"- Workflow: `{spec.workflow_id}`",
            f"- Status: `{status}`",
            f"- Created: `{spec.created_at.isoformat()}`",
            "",
            "## Summary",
            "",
            spec.summary.strip() or "_Empty_",
            "",
            _bullet_section("In scope", spec.in_scope),
            _bullet_section("Out of scope", spec.out_of_scope),
            _bullet_section("Functional requirements", spec.functional_requirements),
            _bullet_section(
                "Non-functional requirements", spec.non_functional_requirements
            ),
            _bullet_section("Acceptance criteria", spec.acceptance_criteria),
            _bullet_section("Assumptions", spec.assumptions),
            _bullet_section("Constraints", spec.constraints),
        ]
        if answers:
            lines.extend(["## Clarifications applied", ""])
            for answer in answers:
                lines.append(f"- **{answer.question_id}:** {answer.answer}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _render_plan(status: str, plan: EngineeringPlan) -> str:
        ready = ready_tasks(plan.tasks, completed_ids=set())
        cohorts = parallel_cohorts(plan.tasks)
        lines = [
            "# Engineering plan",
            "",
            f"- Plan id: `{plan.id}`",
            f"- Workflow: `{plan.workflow_id}`",
            f"- Specification: `{plan.specification_id}`",
            f"- Status: `{status}`",
            f"- Created: `{plan.created_at.isoformat()}`",
            "",
            "## Summary",
            "",
            plan.summary.strip() or "_Empty_",
            "",
            "## Tasks",
            "",
            "```text",
            render_ascii(plan.tasks),
            "```",
            "",
            "## Dependency graph (Mermaid)",
            "",
            "```mermaid",
            render_mermaid(plan.tasks),
            "```",
            "",
            "## Ready set (initial)",
            "",
        ]
        if not ready:
            lines.append("_None_")
        else:
            for task in ready:
                lines.append(f"- `{task.id}` — {task.name}")
        lines.extend(["", "## Parallel cohorts (simulated)", ""])
        if not cohorts:
            lines.append("_None_")
        else:
            for idx, cohort in enumerate(cohorts):
                ids = ", ".join(f"`{t.id}`" for t in cohort)
                lines.append(f"- Cohort {idx}: {ids}")
        lines.append("")
        return "\n".join(lines)
