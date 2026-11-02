"""Interactive end-to-end run prompts (clarification + approval gates)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agentic_engineer.cli.main import app

runner = CliRunner()


def test_interactive_clear_requirement_approves_through_plan(tmp_path: Path) -> None:
    target = tmp_path / "demo"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0

    # No clarification; two approval prompts (spec then plan).
    result = runner.invoke(
        app,
        [
            "run",
            str(target),
            "--interactive",
            "--requirement",
            "Add a /health endpoint that returns status ok and the app version string",
        ],
        input="a\nspec ok\na\nplan ok\n",
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Specification approval" in result.stdout
    assert "Plan approval" in result.stdout
    assert "plan_approved" in result.stdout
    assert (target / ".agentic" / "readable" / "PLAN.md").is_file()


def test_interactive_ambiguous_clarifies_then_approves(tmp_path: Path) -> None:
    target = tmp_path / "ambiguous"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0

    result = runner.invoke(
        app,
        [
            "run",
            str(target),
            "-i",
            "-r",
            "Improve sharing security",
        ],
        input=(
            "Require signed share links that expire in 24 hours\n"
            "Must not break existing public reads\n"
            "a\nok\n"
            "a\nok\n"
        ),
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Clarification required" in result.stdout
    assert "plan_approved" in result.stdout


def test_interactive_reject_spec_stops(tmp_path: Path) -> None:
    target = tmp_path / "reject"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0

    result = runner.invoke(
        app,
        [
            "run",
            str(target),
            "-i",
            "-r",
            "Add a /health endpoint that returns status ok and the app version string",
        ],
        input="r\nnot ready\n",
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "spec_rejected" in result.stdout


def test_explicit_approve_still_works_without_interactive(tmp_path: Path) -> None:
    target = tmp_path / "explicit"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0
    run = runner.invoke(
        app,
        [
            "run",
            str(target),
            "-r",
            "Add a /health endpoint that returns status ok and the app version string",
        ],
    )
    assert run.exit_code == 0
    assert "awaiting_spec_approval" in run.stdout

    approve = runner.invoke(app, ["approve", str(target), "--comment", "ok"])
    assert approve.exit_code == 0
    assert "awaiting_plan_approval" in approve.stdout
