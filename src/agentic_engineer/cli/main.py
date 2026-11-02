"""Typer entrypoint for the `agentic` CLI."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer

from agentic_engineer import __version__
from agentic_engineer.cli.interactive import drive_interactive
from agentic_engineer.config import configure_from_cli
from agentic_engineer.graph.requirement_workflow import (
    RequirementWorkflowService,
    WorkflowError,
)
from agentic_engineer.logging_setup import configure_logging
from agentic_engineer.workspace import (
    Workspace,
    WorkspaceError,
    WorkspaceIsolationError,
    WorkspaceNeedsConfirmation,
)

app = typer.Typer(
    name="agentic",
    help="Agentic Engineer — agentic software engineering CLI.",
    no_args_is_help=True,
)
logger = logging.getLogger(__name__)


def _handle_workspace_errors(exc: Exception) -> None:
    if isinstance(exc, WorkspaceNeedsConfirmation):
        typer.secho(str(exc), fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=2) from exc
    if isinstance(exc, WorkspaceIsolationError):
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=3) from exc
    if isinstance(exc, (WorkspaceError, WorkflowError)):
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    raise exc


def _open_workspace(project_path: str) -> Workspace:
    try:
        return Workspace.open(project_path)
    except (WorkspaceError, WorkspaceIsolationError) as exc:
        _handle_workspace_errors(exc)
        raise


def _print_workflow_status(state, *, readable_root: Path | None = None) -> None:
    typer.echo(f"workflow_id: {state.workflow_id}")
    typer.echo(f"status: {state.status}")
    typer.echo(f"requirement: {state.requirement}")
    if state.analysis and state.status == "awaiting_clarification":
        typer.echo("clarification_questions:")
        for question in state.analysis.clarification_questions:
            if question.essential:
                typer.echo(f"  - [{question.id}] {question.question}")
        typer.echo(
            'Continue with: agentic run <path> --interactive'
            '  OR  agentic run <path> --answer "..." [--answer "..."]'
        )
    if state.specification_id:
        typer.echo(f"specification_id: {state.specification_id}")
    if state.plan_id:
        typer.echo(f"plan_id: {state.plan_id}")
    if state.status == "spec_approved":
        typer.echo(
            "Plan generation stalled — retry with: agentic plan <path> [--generate]"
        )
    if readable_root is not None:
        typer.echo(f"readable_dir: {readable_root}")
        if (readable_root / "SPECIFICATION.md").is_file():
            typer.echo(f"readable_spec: {readable_root / 'SPECIFICATION.md'}")
        if (readable_root / "ANALYSIS.md").is_file():
            typer.echo(f"readable_analysis: {readable_root / 'ANALYSIS.md'}")
        if (readable_root / "PLAN.md").is_file():
            typer.echo(f"readable_plan: {readable_root / 'PLAN.md'}")
    if state.pending_approval_id:
        typer.echo(f"pending_approval_id: {state.pending_approval_id}")
        if state.status == "awaiting_plan_approval":
            typer.echo(
                "Plan gate — agentic run <path> --interactive"
                "  OR  agentic approve <path> | agentic reject <path>"
            )
        elif state.status == "awaiting_spec_approval":
            typer.echo(
                "Spec gate — agentic run <path> --interactive"
                "  OR  agentic approve <path> | agentic reject <path>"
            )
        else:
            typer.echo("Respond with: agentic approve <path> | agentic reject <path>")
    if state.stop_reason:
        typer.echo(f"stop_reason: {state.stop_reason}")


@app.callback()
def _root(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging"),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help=(
            "Path to TOML config (Anthropic credentials, model, etc.). "
            "If omitted, searches AGENTIC_CONFIG, ./agentic.toml, ~/.agentic/config.toml"
        ),
        exists=False,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    try:
        # Always refresh settings so --config / discovered agentic.toml apply.
        settings = configure_from_cli(config_file=config)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    level = "DEBUG" if verbose else settings.log_level
    configure_logging(level)


@app.command("version")
def version() -> None:
    """Print CLI version."""
    typer.echo(__version__)


@app.command("init")
def init_cmd(
    project_path: str = typer.Argument(..., help="Target project path (absolute or relative)"),
    force: bool = typer.Option(
        False,
        "--force",
        "--yes",
        "-y",
        help="Initialize even if the target directory is not empty",
    ),
) -> None:
    """Initialize a target project and create its `.agentic/` directory."""
    try:
        workspace = Workspace.init(project_path, force=force)
    except Exception as exc:  # noqa: BLE001 — mapped below
        _handle_workspace_errors(exc)
        return

    typer.echo(f"Initialized workspace: {workspace.root}")
    typer.echo(f"Agentic metadata: {workspace.agentic_dir}")


def _load_requirement_text(
    *,
    requirement: str | None,
    requirement_file: Path | None,
) -> str:
    """Resolve inline requirement or multiline text from a file."""
    if requirement and requirement_file:
        raise WorkflowError("Pass either --requirement or --requirement-file, not both")
    if requirement_file is not None:
        path = requirement_file.expanduser()
        if not path.is_file():
            raise WorkflowError(f"Requirement file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise WorkflowError(f"Requirement file is empty: {path}")
        return text
    if requirement is not None:
        text = requirement.strip()
        if not text:
            raise WorkflowError("Requirement must not be empty")
        return text
    raise WorkflowError("Internal error: no requirement source provided")


def _show_spec_for_interactive(service: RequirementWorkflowService, state) -> None:
    md_path = service.readable_root() / "SPECIFICATION.md"
    typer.echo("")
    if md_path.is_file():
        typer.echo(md_path.read_text(encoding="utf-8"))
    elif state.specification is not None:
        typer.echo(json.dumps(state.specification.model_dump(mode="json"), indent=2))


def _show_plan_for_interactive(service: RequirementWorkflowService, state) -> None:
    typer.echo("")
    if state.plan is not None:
        typer.echo(service.format_plan_display(state.plan))
        return
    md_path = service.readable_root() / "PLAN.md"
    if md_path.is_file():
        typer.echo(md_path.read_text(encoding="utf-8"))


@app.command("run")
def run_cmd(
    project_path: str = typer.Argument(..., help="Target project path"),
    requirement: Optional[str] = typer.Option(
        None,
        "--requirement",
        "-r",
        help="Natural-language requirement (starts a new workflow)",
    ),
    requirement_file: Optional[Path] = typer.Option(
        None,
        "--requirement-file",
        "-R",
        help="Path to a text/markdown file with the requirement (multiline OK)",
        exists=False,
        dir_okay=False,
        readable=True,
    ),
    answer: Optional[list[str]] = typer.Option(
        None,
        "--answer",
        "-a",
        help="Clarification answer (repeatable). Continues an awaiting-clarification workflow.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help=(
            "Drive end-to-end in this session: auto-advance generation/validation, "
            "and prompt inline for clarification / approve / reject. "
            "Explicit approve/reject/--answer commands still work without this flag."
        ),
    ),
) -> None:
    """Start or continue the requirement-intelligence workflow."""
    workspace = _open_workspace(project_path)
    service = RequirementWorkflowService(workspace)
    try:
        has_req = bool(requirement) or requirement_file is not None
        if has_req and answer:
            raise WorkflowError(
                "Pass either a requirement (--requirement / --requirement-file) "
                "or --answer, not both"
            )
        if answer and interactive:
            raise WorkflowError(
                "Pass either --answer or --interactive, not both "
                "(interactive will prompt for answers)"
            )
        if has_req:
            text = _load_requirement_text(
                requirement=requirement,
                requirement_file=requirement_file,
            )
            state = service.start(text)
        elif answer:
            state = service.provide_answers(list(answer))
        elif interactive:
            # Resume parked workflow and continue prompting through remaining gates.
            state = service.load_active()
        else:
            raise WorkflowError(
                "Provide --requirement or --requirement-file to start, "
                "--answer to continue clarification, "
                "or --interactive to resume and prompt through human gates"
            )

        if interactive:
            state = drive_interactive(
                service,
                state,
                show_status=lambda s: _print_workflow_status(
                    s, readable_root=service.readable_root()
                ),
                show_spec=lambda s: _show_spec_for_interactive(service, s),
                show_plan=lambda s: _show_plan_for_interactive(service, s),
            )
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return

    _print_workflow_status(state, readable_root=service.readable_root())


@app.command("status")
def status_cmd(
    project_path: str = typer.Argument(..., help="Target project path"),
) -> None:
    """Show workspace and active workflow status."""
    workspace = _open_workspace(project_path)
    config = workspace.load_config()
    typer.echo(f"root: {workspace.root}")
    typer.echo(f"schema_version: {config.schema_version}")
    typer.echo(f"active_workflow_id: {config.active_workflow_id or '(none)'}")
    typer.echo(
        f"active_specification_id: {config.active_specification_id or '(none)'}"
    )
    typer.echo(f"active_plan_id: {config.active_plan_id or '(none)'}")
    if not config.active_workflow_id:
        typer.echo("phase: initialized (no active workflow)")
        return
    service = RequirementWorkflowService(workspace)
    try:
        state = service.load_active()
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return
    _print_workflow_status(state, readable_root=service.readable_root())


@app.command("spec")
def spec_cmd(
    project_path: str = typer.Argument(..., help="Target project path"),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print machine-readable JSON instead of Markdown",
    ),
) -> None:
    """Print the active specification (Markdown by default)."""
    workspace = _open_workspace(project_path)
    service = RequirementWorkflowService(workspace)
    try:
        state = service.load_active()
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return
    if state.specification is None:
        typer.secho("No specification generated yet.", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=1)
    if as_json:
        typer.echo(json.dumps(state.specification.model_dump(mode="json"), indent=2))
        return
    md_path = service.readable_root() / "SPECIFICATION.md"
    if md_path.is_file():
        typer.echo(md_path.read_text(encoding="utf-8"))
        return
    # Fallback if readable file was not written (older workspaces).
    typer.echo(json.dumps(state.specification.model_dump(mode="json"), indent=2))


@app.command("plan")
def plan_cmd(
    project_path: str = typer.Argument(..., help="Target project path"),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print machine-readable JSON instead of ASCII/Mermaid",
    ),
    generate: bool = typer.Option(
        False,
        "--generate",
        "-g",
        help="Force regeneration when the current status allows it",
    ),
) -> None:
    """Generate or show the engineering task plan / dependency graph."""
    workspace = _open_workspace(project_path)
    service = RequirementWorkflowService(workspace)
    try:
        state = service.plan_or_show(generate=generate)
        plan = state.plan
        if plan is None:
            plan = service.get_plan()
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return

    _print_workflow_status(state, readable_root=service.readable_root())
    typer.echo("")
    if as_json:
        typer.echo(json.dumps(plan.model_dump(mode="json"), indent=2))
        return
    md_path = service.readable_root() / "PLAN.md"
    if md_path.is_file() and state.status in (
        "awaiting_plan_approval",
        "plan_approved",
        "plan_rejected",
        "stopped",
    ):
        # Prefer live ASCII/Mermaid display for operators; Markdown stays on disk.
        pass
    typer.echo(service.format_plan_display(plan))


@app.command("approve")
def approve_cmd(
    project_path: str = typer.Argument(..., help="Target project path"),
    comment: Optional[str] = typer.Option(None, "--comment", "-c"),
) -> None:
    """Approve the pending specification or plan (human decision)."""
    workspace = _open_workspace(project_path)
    service = RequirementWorkflowService(workspace)
    try:
        before = service.load_active()
        state = service.approve(comment=comment)
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return
    if before.status == "awaiting_plan_approval":
        typer.secho("Plan approved.", fg=typer.colors.GREEN)
    elif state.status == "awaiting_plan_approval":
        typer.secho(
            "Specification approved; plan generated — awaiting plan approval.",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho("Specification approved.", fg=typer.colors.GREEN)
    _print_workflow_status(state, readable_root=service.readable_root())


@app.command("reject")
def reject_cmd(
    project_path: str = typer.Argument(..., help="Target project path"),
    comment: Optional[str] = typer.Option(None, "--comment", "-c"),
    changes: bool = typer.Option(
        False,
        "--changes-requested",
        help="Record as changes_requested instead of rejected",
    ),
) -> None:
    """Reject the pending specification or plan (human decision)."""
    workspace = _open_workspace(project_path)
    service = RequirementWorkflowService(workspace)
    try:
        before = service.load_active()
        state = service.reject(comment=comment, changes_requested=changes)
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return
    label = "Plan" if before.status == "awaiting_plan_approval" else "Specification"
    typer.secho(f"{label} decision recorded.", fg=typer.colors.YELLOW)
    _print_workflow_status(state, readable_root=service.readable_root())


def run(argv: Optional[list[str]] = None) -> None:
    """Programmatic entry for tests."""
    app(args=argv, standalone_mode=True)


if __name__ == "__main__":
    app()
