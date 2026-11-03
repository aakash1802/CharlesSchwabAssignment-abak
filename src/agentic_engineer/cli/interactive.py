"""Interactive stdin prompts for clarification and approval gates.

Used by `agentic run --interactive`. Explicit `approve` / `reject` / `--answer`
remain available for non-interactive / resume-after-exit workflows.
"""

from __future__ import annotations

from collections.abc import Callable

import typer

from agentic_engineer.graph.requirement_workflow import (
    RequirementWorkflowService,
    WorkflowError,
)
from agentic_engineer.models.workflow import RequirementWorkflowState

ApprovalChoice = str  # approve | reject | changes


def prompt_clarification_answers(state: RequirementWorkflowState) -> list[str]:
    """Ask each essential clarification question on stdin."""
    if state.analysis is None:
        raise WorkflowError("Missing analysis for clarification prompts")
    questions = [q for q in state.analysis.clarification_questions if q.essential]
    if not questions:
        raise WorkflowError("No essential clarification questions to answer")

    typer.secho("\n=== Clarification required ===", fg=typer.colors.YELLOW)
    typer.echo("Answer each question (empty answer is not allowed).\n")
    answers: list[str] = []
    for question in questions:
        typer.echo(f"[{question.id}] {question.question}")
        if question.reason:
            typer.echo(f"  reason: {question.reason}")
        while True:
            value = typer.prompt("Your answer").strip()
            if value:
                answers.append(value)
                break
            typer.secho("Answer cannot be empty.", fg=typer.colors.RED, err=True)
    return answers


def prompt_approval(
    *,
    gate_label: str,
    artifact_hint: str | None = None,
) -> tuple[ApprovalChoice, str | None]:
    """Prompt for approve / reject / changes-requested at a human gate."""
    typer.secho(f"\n=== {gate_label} ===", fg=typer.colors.YELLOW)
    if artifact_hint:
        typer.echo(artifact_hint)
    typer.echo(
        "Choose: [a]pprove / [r]eject / [c]hanges-requested "
        "(or full words: approve, reject, changes)"
    )
    while True:
        raw = typer.prompt("Decision").strip().lower()
        if raw in {"a", "approve", "yes", "y"}:
            choice: ApprovalChoice = "approve"
            break
        if raw in {"r", "reject", "no", "n"}:
            choice = "reject"
            break
        if raw in {"c", "changes", "changes-requested", "changes_requested"}:
            choice = "changes"
            break
        typer.secho(
            "Enter a/approve, r/reject, or c/changes.",
            fg=typer.colors.RED,
            err=True,
        )
    comment_raw = typer.prompt("Comment (optional)", default="", show_default=False)
    comment = comment_raw.strip() or None
    return choice, comment


def _apply_approval_choice(
    service: RequirementWorkflowService,
    choice: ApprovalChoice,
    comment: str | None,
) -> RequirementWorkflowState:
    if choice == "approve":
        return service.approve(comment=comment)
    if choice == "changes":
        return service.reject(comment=comment, changes_requested=True)
    return service.reject(comment=comment, changes_requested=False)


def _format_command_hint(state: RequirementWorkflowState) -> str:
    proposal = state.pending_command
    if proposal is None:
        return "Command proposal pending."
    if proposal.kind == "shell":
        cmd = proposal.shell or ""
    else:
        cmd = " ".join(proposal.argv)
    lines = [
        f"proposal_id: {proposal.proposal_id}",
        f"command: {cmd}",
        f"cwd: {proposal.cwd_relative}",
    ]
    if proposal.reason:
        lines.append(f"reason: {proposal.reason}")
    if proposal.task_id:
        lines.append(f"task_id: {proposal.task_id}")
    return "\n".join(lines)


def _format_destructive_hint(state: RequirementWorkflowState) -> str:
    proposal = state.pending_destructive
    if proposal is None:
        return "Destructive action pending."
    return (
        f"proposal_id: {proposal.proposal_id}\n"
        f"action: {proposal.action}\n"
        f"paths: {', '.join(proposal.paths)}\n"
        f"reason: {proposal.reason}"
    )


def drive_interactive(
    service: RequirementWorkflowService,
    state: RequirementWorkflowState,
    *,
    show_status: Callable[[RequirementWorkflowState], None],
    show_spec: Callable[[RequirementWorkflowState], None] | None = None,
    show_plan: Callable[[RequirementWorkflowState], None] | None = None,
) -> RequirementWorkflowState:
    """Advance automatically; interrupt only when human input is required."""
    terminal = {
        "plan_rejected",
        "spec_rejected",
        "stopped",
        "completed",
        "safe_stopped",
    }

    while state.status not in terminal:
        show_status(state)

        if state.status == "awaiting_clarification":
            answers = prompt_clarification_answers(state)
            state = service.provide_answers(answers)
            continue

        if state.status == "awaiting_spec_approval":
            if show_spec is not None:
                show_spec(state)
            choice, comment = prompt_approval(
                gate_label="Specification approval",
                artifact_hint=(
                    f"specification_id: {state.specification_id}\n"
                    "Review readable SPECIFICATION.md (shown above when available)."
                ),
            )
            state = _apply_approval_choice(service, choice, comment)
            continue

        if state.status == "awaiting_plan_approval":
            if show_plan is not None:
                show_plan(state)
            choice, comment = prompt_approval(
                gate_label="Plan approval",
                artifact_hint=(
                    f"plan_id: {state.plan_id}\n"
                    "Review the task graph (shown above when available)."
                ),
            )
            state = _apply_approval_choice(service, choice, comment)
            continue

        if state.status == "spec_approved":
            # Auto-plan normally follows spec approve; allow interactive retry.
            typer.secho(
                "Retrying plan generation…",
                fg=typer.colors.YELLOW,
            )
            state = service.generate_plan()
            continue

        if state.status == "plan_approved":
            typer.secho(
                "Starting execution — inspect → schedule cohorts → run agents "
                "(progress lines appear as each step runs)…",
                fg=typer.colors.CYAN,
            )
            state = service.start_execution()
            continue

        if state.status == "awaiting_command_approval":
            choice, comment = prompt_approval(
                gate_label="Command approval (approve-before-run)",
                artifact_hint=_format_command_hint(state),
            )
            # changes-requested is treated as reject for command gates
            state = _apply_approval_choice(service, choice, comment)
            continue

        if state.status == "awaiting_destructive_approval":
            choice, comment = prompt_approval(
                gate_label="Destructive action approval",
                artifact_hint=_format_destructive_hint(state),
            )
            state = _apply_approval_choice(service, choice, comment)
            continue

        if state.status == "awaiting_release_approval":
            choice, comment = prompt_approval(
                gate_label="Release approval (success path)",
                artifact_hint=(
                    "Review .agentic/readable/REPORT.md and reports/ before complete."
                ),
            )
            state = _apply_approval_choice(service, choice, comment)
            continue

        if state.status == "executing":
            # Mid-flight without a human gate — continue/resume graph.
            typer.secho(
                "Resuming execution from checkpoint…",
                fg=typer.colors.CYAN,
            )
            state = service.start_execution()
            continue

        # Unexpected mid-phase statuses should not spin forever.
        raise WorkflowError(
            f"Interactive driver cannot continue from status={state.status}"
        )

    return state
