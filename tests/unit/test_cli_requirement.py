"""CLI requirement intelligence commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agentic_engineer.cli.main import app

runner = CliRunner()


def test_cli_ambiguous_clarify_approve_spec(tmp_path: Path) -> None:
    target = tmp_path / "demo"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0

    run = runner.invoke(
        app,
        ["run", str(target), "--requirement", "Improve sharing security"],
    )
    assert run.exit_code == 0, run.stdout + run.stderr
    assert "awaiting_clarification" in run.stdout

    status = runner.invoke(app, ["status", str(target)])
    assert status.exit_code == 0
    assert "awaiting_clarification" in status.stdout

    cont = runner.invoke(
        app,
        [
            "run",
            str(target),
            "--answer",
            "Require signed share links that expire in 24 hours",
            "--answer",
            "Must not break existing public read links",
        ],
    )
    assert cont.exit_code == 0, cont.stdout + cont.stderr
    assert "awaiting_spec_approval" in cont.stdout

    approve = runner.invoke(app, ["approve", str(target), "--comment", "ok"])
    assert approve.exit_code == 0, approve.stdout + approve.stderr
    assert "spec_approved" in approve.stdout

    spec = runner.invoke(app, ["spec", str(target)])
    assert spec.exit_code == 0, spec.stdout + spec.stderr
    assert "functional_requirements" in spec.stdout
    assert "signed share links" in spec.stdout.lower() or "Clarified" in spec.stdout


def test_cli_reject(tmp_path: Path) -> None:
    target = tmp_path / "demo2"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0
    run = runner.invoke(
        app,
        [
            "run",
            str(target),
            "--requirement",
            "Add a /health endpoint returning status and version",
        ],
    )
    assert run.exit_code == 0
    rejected = runner.invoke(app, ["reject", str(target), "--comment", "rework"])
    assert rejected.exit_code == 0
    assert "spec_rejected" in rejected.stdout
