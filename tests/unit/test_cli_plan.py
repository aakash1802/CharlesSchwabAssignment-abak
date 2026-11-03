"""CLI plan command and plan approval gate."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agentic_engineer.cli.main import app

runner = CliRunner()


def _approve_spec_auto_plans(target: Path) -> None:
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0
    run = runner.invoke(
        app,
        [
            "run",
            str(target),
            "--requirement",
            "Add a /health endpoint that returns status ok and the app version string",
        ],
    )
    assert run.exit_code == 0, run.stdout + run.stderr
    approve = runner.invoke(app, ["approve", str(target), "--comment", "spec ok"])
    assert approve.exit_code == 0, approve.stdout + approve.stderr
    assert "awaiting_plan_approval" in approve.stdout


def test_cli_plan_approve_and_show(tmp_path: Path) -> None:
    target = tmp_path / "demo"
    _approve_spec_auto_plans(target)

    # Spec approve already generated the plan; `plan` shows it.
    plan = runner.invoke(app, ["plan", str(target)])
    assert plan.exit_code == 0, plan.stdout + plan.stderr
    assert "awaiting_plan_approval" in plan.stdout
    assert "flowchart TD" in plan.stdout
    assert "parallel_cohorts:" in plan.stdout
    assert "t1" in plan.stdout

    approve = runner.invoke(app, ["approve", str(target), "--comment", "plan ok"])
    assert approve.exit_code == 0, approve.stdout + approve.stderr
    assert "Plan approved" in approve.stdout
    assert "Execution started" in approve.stdout
    # Plan approve auto-starts execution and parks at the next human gate.
    assert (
        "awaiting_command_approval" in approve.stdout
        or "awaiting_release_approval" in approve.stdout
        or "completed" in approve.stdout
    )

    show = runner.invoke(app, ["plan", str(target)])
    assert show.exit_code == 0, show.stdout + show.stderr
    assert "t3" in show.stdout and "t4" in show.stdout

    plan_json = runner.invoke(app, ["plan", str(target), "--json"])
    assert plan_json.exit_code == 0, plan_json.stdout + plan_json.stderr
    assert '"tasks"' in plan_json.stdout

    readable = target / ".agentic" / "readable"
    assert (readable / "PLAN.md").is_file()
    assert (readable / "phases" / "05_plan.md").is_file()
    assert (readable / "phases" / "06_plan_approval.md").is_file()

def test_cli_plan_without_spec_fails(tmp_path: Path) -> None:
    target = tmp_path / "early"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0
    result = runner.invoke(app, ["plan", str(target)])
    assert result.exit_code != 0
