"""CommandRunner approve-before-run unit tests (AC-P4-4, AC-P4-7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_engineer.execution.commands import CommandRunner, CommandRunnerError
from agentic_engineer.workspace import Workspace


def test_reject_does_not_run(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    runner = CommandRunner(ws)
    proposal = runner.propose_argv(
        ["python", "-c", "raise SystemExit('should-not-run')"],
        reason="demo",
    )
    evidence = runner.rejected_evidence(proposal)
    assert evidence.approved is False
    assert evidence.exit_code == -1
    assert "not executed" in evidence.stderr


def test_approve_runs_with_capture(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    runner = CommandRunner(ws)
    proposal = runner.propose_argv(
        ["python", "-c", "print('hello-phase4')"],
        reason="capture demo",
    )
    evidence = runner.run_approved(proposal)
    assert evidence.approved is True
    assert evidence.exit_code == 0
    assert "hello-phase4" in evidence.stdout
    assert evidence.passed is True


def test_cwd_contained_to_workspace(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    (ws.root / "sub").mkdir()
    runner = CommandRunner(ws)
    proposal = runner.propose_argv(
        ["python", "-c", "import os; print(os.getcwd())"],
        cwd_relative="sub",
    )
    evidence = runner.run_approved(proposal)
    assert evidence.exit_code == 0
    assert str(ws.root / "sub") in evidence.stdout.replace("/", "\\") or str(
        ws.root / "sub"
    ) in evidence.stdout


def test_cwd_escape_rejected(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    runner = CommandRunner(ws)
    with pytest.raises(Exception):
        runner.propose_argv(["python", "-c", "print(1)"], cwd_relative="../outside")


def test_empty_argv_rejected(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "target")
    runner = CommandRunner(ws)
    with pytest.raises(CommandRunnerError):
        runner.propose_argv([])
