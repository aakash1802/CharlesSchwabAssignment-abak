"""Human-readable Markdown artifacts (R13)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agentic_engineer.cli.main import app

runner = CliRunner()


def test_clear_requirement_writes_analysis_spec_and_phase_files(tmp_path: Path) -> None:
    target = tmp_path / "demo-clear"
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
    assert run.exit_code == 0, run.stdout + run.stderr
    assert "readable_dir:" in run.stdout

    readable = target / ".agentic" / "readable"
    assert (readable / "ANALYSIS.md").is_file()
    assert (readable / "SPECIFICATION.md").is_file()
    assert (readable / "phases" / "01_analysis.md").is_file()
    assert not (readable / "phases" / "02_clarification.md").is_file()
    assert (readable / "phases" / "03_specification.md").is_file()

    analysis = (readable / "ANALYSIS.md").read_text(encoding="utf-8")
    assert "# Requirement analysis" in analysis
    assert "/health" in analysis

    approve = runner.invoke(app, ["approve", str(target)])
    assert approve.exit_code == 0
    assert (readable / "phases" / "04_approval.md").is_file()
    approval = (readable / "phases" / "04_approval.md").read_text(encoding="utf-8")
    assert "approved" in approval


def test_init_creates_readable_dirs(tmp_path: Path) -> None:
    target = tmp_path / "demo-init"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0
    assert (target / ".agentic" / "readable").is_dir()
    assert (target / ".agentic" / "readable" / "phases").is_dir()
