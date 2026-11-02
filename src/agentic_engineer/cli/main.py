"""Typer entrypoint for the `agentic` CLI."""

from __future__ import annotations

import json
import logging
from typing import Optional

import typer

from agentic_engineer import __version__
from agentic_engineer.config import get_settings
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


def _print_workflow_status(state) -> None:
    typer.echo(f"workflow_id: {state.workflow_id}")
    typer.echo(f"status: {state.status}")
    typer.echo(f"requirement: {state.requirement}")
    if state.analysis and state.status == "awaiting_clarification":
        typer.echo("clarification_questions:")
        for question in state.analysis.clarification_questions:
            if question.essential:
                typer.echo(f"  - [{question.id}] {question.question}")
        typer.echo(
            'Continue with: agentic run <path> --answer "..." [--answer "..."]'
        )
    if state.specification_id:
        typer.echo(f"specification_id: {state.specification_id}")
    if state.pending_approval_id:
        typer.echo(f"pending_approval_id: {state.pending_approval_id}")
        typer.echo("Respond with: agentic approve <path> | agentic reject <path>")
    if state.stop_reason:
        typer.echo(f"stop_reason: {state.stop_reason}")


@app.callback()
def _root(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging"),
) -> None:
    settings = get_settings()
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


@app.command("run")
def run_cmd(
    project_path: str = typer.Argument(..., help="Target project path"),
    requirement: Optional[str] = typer.Option(
        None,
        "--requirement",
        "-r",
        help="Natural-language requirement (starts a new workflow)",
    ),
    answer: Optional[list[str]] = typer.Option(
        None,
        "--answer",
        "-a",
        help="Clarification answer (repeatable). Continues an awaiting-clarification workflow.",
    ),
) -> None:
    """Start or continue the requirement-intelligence workflow."""
    workspace = _open_workspace(project_path)
    service = RequirementWorkflowService(workspace)
    try:
        if requirement and answer:
            raise WorkflowError("Pass either --requirement or --answer, not both")
        if requirement:
            state = service.start(requirement)
        elif answer:
            state = service.provide_answers(list(answer))
        else:
            raise WorkflowError(
                "Provide --requirement to start, or --answer to continue clarification"
            )
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return

    _print_workflow_status(state)


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
    if not config.active_workflow_id:
        typer.echo("phase: initialized (no active workflow)")
        return
    try:
        state = RequirementWorkflowService(workspace).load_active()
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return
    _print_workflow_status(state)


@app.command("spec")
def spec_cmd(
    project_path: str = typer.Argument(..., help="Target project path"),
) -> None:
    """Print the active specification JSON."""
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
    typer.echo(json.dumps(state.specification.model_dump(mode="json"), indent=2))


@app.command("approve")
def approve_cmd(
    project_path: str = typer.Argument(..., help="Target project path"),
    comment: Optional[str] = typer.Option(None, "--comment", "-c"),
) -> None:
    """Approve the pending specification (human decision)."""
    workspace = _open_workspace(project_path)
    try:
        state = RequirementWorkflowService(workspace).approve(comment=comment)
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return
    typer.secho("Specification approved.", fg=typer.colors.GREEN)
    _print_workflow_status(state)


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
    """Reject the pending specification (human decision)."""
    workspace = _open_workspace(project_path)
    try:
        state = RequirementWorkflowService(workspace).reject(
            comment=comment, changes_requested=changes
        )
    except WorkflowError as exc:
        _handle_workspace_errors(exc)
        return
    typer.secho("Specification decision recorded.", fg=typer.colors.YELLOW)
    _print_workflow_status(state)


def run(argv: Optional[list[str]] = None) -> None:
    """Programmatic entry for tests."""
    app(args=argv, standalone_mode=True)


if __name__ == "__main__":
    app()
