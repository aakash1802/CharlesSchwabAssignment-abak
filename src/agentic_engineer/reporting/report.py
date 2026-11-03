"""Build machine + human-readable workflow reports from real artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentic_engineer.audit.metrics import MetricsSnapshot, derive_metrics, write_metrics
from agentic_engineer.execution.events import ExecutionEventLog
from agentic_engineer.governance.approvals import ApprovalService
from agentic_engineer.models.common import utc_now
from agentic_engineer.models.execution import ExecutionEvent
from agentic_engineer.models.workflow import RequirementWorkflowState
from agentic_engineer.persistence.json_store import JsonStore
from agentic_engineer.persistence.readable_store import ReadableArtifactStore


class ReportDocument(BaseModel):
    schema_version: int = 1
    workflow_id: str
    status: str
    requirement: str
    summary: str
    specification_id: str | None = None
    plan_id: str | None = None
    stop_reason: str | None = None
    design_note: str | None = None
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    written_paths: list[str] = Field(default_factory=list)
    test_results: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())


class ReportBuilder:
    def __init__(self, agentic_dir: Path) -> None:
        self._agentic = agentic_dir
        self._readable = ReadableArtifactStore(agentic_dir)
        self._reports = agentic_dir / "reports"
        self._reports.mkdir(parents=True, exist_ok=True)

    def build(self, state: RequirementWorkflowState) -> ReportDocument:
        workflow_dir = self._agentic / "workflows" / state.workflow_id
        events = ExecutionEventLog(workflow_dir).list_events()
        metrics = derive_metrics(state.workflow_id, events)
        write_metrics(workflow_dir, metrics)
        approvals = [
            r.model_dump(mode="json")
            for r in ApprovalService(workflow_dir).list_all()
        ]
        tasks: list[dict[str, Any]] = []
        if state.plan is not None:
            tasks = [t.model_dump(mode="json") for t in state.plan.tasks]
        summary = self._summary_line(state, metrics, events)
        return ReportDocument(
            workflow_id=state.workflow_id,
            status=state.status,
            requirement=state.requirement,
            summary=summary,
            specification_id=state.specification_id,
            plan_id=state.plan_id,
            stop_reason=state.stop_reason,
            design_note=state.design_note,
            tasks=tasks,
            approvals=approvals,
            events=[e.model_dump(mode="json") for e in events],
            metrics=metrics.model_dump(mode="json"),
            written_paths=[],
            test_results=[t.model_dump(mode="json") for t in state.test_results],
        )

    def write(self, state: RequirementWorkflowState) -> tuple[Path, Path]:
        doc = self.build(state)
        json_path = self._reports / f"report_{state.workflow_id}.json"
        JsonStore(self._reports).write_json(
            json_path.name,
            doc.model_dump(mode="json"),
        )
        md = self._render_markdown(doc)
        md_path = self._readable.write_report(md)
        return json_path, md_path

    def format_history(self, state: RequirementWorkflowState) -> str:
        workflow_dir = self._agentic / "workflows" / state.workflow_id
        events = ExecutionEventLog(workflow_dir).list_events()
        if not events:
            return "No audit events recorded."
        lines = [f"Audit history for `{state.workflow_id}` ({len(events)} events)", ""]
        for event in events:
            ts = event.created_at.isoformat() if event.created_at else ""
            task = f" task={event.task_id}" if event.task_id else ""
            msg = f" — {event.message}" if event.message else ""
            lines.append(f"- [{ts}] {event.event_type}{task}{msg}")
        return "\n".join(lines)

    def format_cli_summary(self, state: RequirementWorkflowState) -> str:
        doc = self.build(state)
        metrics = MetricsSnapshot.model_validate(doc.metrics)
        lines = [
            f"workflow_id: {doc.workflow_id}",
            f"status: {doc.status}",
            f"summary: {doc.summary}",
            "",
            "metrics (from events only):",
            f"  event_count: {metrics.event_count}",
            f"  task_finishes: {metrics.task_finishes}",
            f"  task_failures: {metrics.task_failures}",
            f"  retries: {metrics.retries}",
            f"  same_operation_retries: {metrics.same_operation_retries}",
            f"  corrected_retries: {metrics.corrected_retries}",
            f"  scope_reductions: {metrics.scope_reductions}",
            f"  replans: {metrics.replans}",
            f"  escalations: {metrics.escalations}",
            f"  recovery_decisions: {metrics.recovery_decisions}",
            f"  safe_stops: {metrics.safe_stops}",
            f"  completed_flag: {metrics.completed}",
        ]
        if metrics.insufficient_data:
            lines.append("insufficient_data:")
            for item in metrics.insufficient_data:
                lines.append(f"  - {item}")
        lines.extend(
            [
                "",
                f"report_json: .agentic/reports/report_{state.workflow_id}.json",
                "report_md: .agentic/readable/REPORT.md",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _summary_line(
        state: RequirementWorkflowState,
        metrics: MetricsSnapshot,
        events: list[ExecutionEvent],
    ) -> str:
        if state.status == "completed":
            return "Workflow completed after release approval."
        if state.status == "awaiting_release_approval":
            return "Execution succeeded; awaiting release approval."
        if state.status == "safe_stopped":
            return f"Safe-stopped: {state.stop_reason or 'see events'}"
        if state.status == "awaiting_plan_approval" and any(
            e.event_type == "replan" for e in events
        ):
            return "Material replan pending plan re-approval."
        if not events:
            return "No execution audit events yet."
        return (
            f"Status `{state.status}` with {metrics.event_count} audit events "
            f"({metrics.task_finishes} finishes, {metrics.task_failures} failures)."
        )

    @staticmethod
    def _render_markdown(doc: ReportDocument) -> str:
        lines = [
            "# Engineering report",
            "",
            f"- Workflow: `{doc.workflow_id}`",
            f"- Status: `{doc.status}`",
            f"- Generated: `{doc.generated_at}`",
            "",
            "## Summary",
            "",
            doc.summary,
            "",
            "## Requirement",
            "",
            doc.requirement,
            "",
            "## Artifacts",
            "",
            f"- Specification: `{doc.specification_id or '(none)'}`",
            f"- Plan: `{doc.plan_id or '(none)'}`",
            f"- Stop reason: {doc.stop_reason or '(none)'}",
            "",
            "## Design note",
            "",
            doc.design_note or "_None_",
            "",
            "## Tasks",
            "",
        ]
        if not doc.tasks:
            lines.append("_None_")
        else:
            for task in doc.tasks:
                lines.append(
                    f"- `{task.get('id')}` [{task.get('status')}] "
                    f"{task.get('name')} (retries={task.get('retry_count', 0)})"
                )
        lines.extend(["", "## Approvals", ""])
        if not doc.approvals:
            lines.append("_None_")
        else:
            for appr in doc.approvals:
                lines.append(
                    f"- `{appr.get('id')}` {appr.get('approval_type')} → "
                    f"**{appr.get('decision')}** — {appr.get('requested_action')}"
                )
        recovery_events = [
            e
            for e in doc.events
            if e.get("event_type")
            in {
                "recovery_decision",
                "retry",
                "scope_reduced",
                "replan",
                "escalation",
                "fail_analyzed",
            }
        ]
        lines.extend(["", "## Recovery", ""])
        if not recovery_events:
            lines.append("_No recovery events_")
        else:
            for event in recovery_events[-30:]:
                details = event.get("details") or {}
                strategy = details.get("strategy") or ""
                category = details.get("failure_category") or ""
                extra = ""
                if strategy or category:
                    extra = f" (strategy={strategy or '—'}, category={category or '—'})"
                lines.append(
                    f"- `{event.get('event_type')}`{extra} "
                    f"{event.get('message') or ''}".rstrip()
                )

        lines.extend(["", "## Metrics", "", "```json"])
        lines.append(json.dumps(doc.metrics, indent=2))
        lines.extend(["```", "", "## Recent events", ""])
        recent = doc.events[-20:]
        if not recent:
            lines.append("_None_")
        else:
            for event in recent:
                lines.append(
                    f"- `{event.get('event_type')}` "
                    f"{event.get('message') or ''}".rstrip()
                )
        lines.append("")
        return "\n".join(lines)
