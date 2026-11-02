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
    assert "awaiting_plan_approval" in approve.stdout
    assert "plan generated" in approve.stdout.lower()

    spec = runner.invoke(app, ["spec", str(target)])
    assert spec.exit_code == 0, spec.stdout + spec.stderr
    assert "Functional requirements" in spec.stdout
    assert "signed share links" in spec.stdout.lower() or "Clarified" in spec.stdout

    readable = target / ".agentic" / "readable"
    assert (readable / "ANALYSIS.md").is_file()
    assert (readable / "SPECIFICATION.md").is_file()
    assert (readable / "PLAN.md").is_file()
    assert (readable / "phases" / "01_analysis.md").is_file()
    assert (readable / "phases" / "02_clarification.md").is_file()
    assert (readable / "phases" / "03_specification.md").is_file()
    assert (readable / "phases" / "04_approval.md").is_file()
    assert (readable / "phases" / "05_plan.md").is_file()
    assert "signed share links" in (readable / "SPECIFICATION.md").read_text(
        encoding="utf-8"
    ).lower() or "Clarified" in (readable / "SPECIFICATION.md").read_text(
        encoding="utf-8"
    )

    spec_json = runner.invoke(app, ["spec", str(target), "--json"])
    assert spec_json.exit_code == 0, spec_json.stdout + spec_json.stderr
    assert "functional_requirements" in spec_json.stdout


def test_cli_requirement_file_multiline(tmp_path: Path) -> None:
    target = tmp_path / "demo-file"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0

    req = tmp_path / "requirement.md"
    req.write_text(
        "Improve sharing security.\n\n"
        "Notes:\n"
        "- Prefer expiring signed links\n"
        "- Keep public reads working\n",
        encoding="utf-8",
    )

    run = runner.invoke(
        app,
        ["run", str(target), "--requirement-file", str(req)],
    )
    assert run.exit_code == 0, run.stdout + run.stderr
    assert "awaiting_clarification" in run.stdout
    assert "Improve sharing security" in run.stdout

    both = runner.invoke(
        app,
        [
            "run",
            str(target),
            "--requirement",
            "x",
            "--requirement-file",
            str(req),
        ],
    )
    assert both.exit_code == 1
    assert "either --requirement or --requirement-file" in (both.stdout + both.stderr)


def test_cli_requirement_file_missing(tmp_path: Path) -> None:
    target = tmp_path / "demo-missing"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0
    missing = tmp_path / "nope.md"
    run = runner.invoke(
        app,
        ["run", str(target), "--requirement-file", str(missing)],
    )
    assert run.exit_code == 1
    assert "not found" in (run.stdout + run.stderr).lower()


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
