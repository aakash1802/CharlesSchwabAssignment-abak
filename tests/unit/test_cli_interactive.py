"""Interactive end-to-end run prompts (clarification + approval gates)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentic_engineer.cli.main import app
from agentic_engineer.config.settings import clear_settings_cache

runner = CliRunner()

# Spec + plan + testing-command + release gates (mock diamond plan).
_HAPPY_APPROVALS = "a\nspec ok\na\nplan ok\na\ncmd ok\na\nrelease ok\n"


@pytest.fixture(autouse=True)
def _force_mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTIC_LLM_PROVIDER", "mock")
    monkeypatch.delenv("AGENTIC_CONFIG", raising=False)
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_interactive_clear_requirement_approves_through_plan(tmp_path: Path) -> None:
    target = tmp_path / "demo"
    assert runner.invoke(app, ["init", str(target)]).exit_code == 0

    result = runner.invoke(
        app,
        [
            "run",
            str(target),
            "--interactive",
            "--requirement",
            "Add a /health endpoint that returns status ok and the app version string",
        ],
        input=_HAPPY_APPROVALS,
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Specification approval" in result.stdout
    assert "Plan approval" in result.stdout
    assert "Command approval" in result.stdout
    assert "plan_approved" in result.stdout
    assert "Starting execution" in result.stdout
    assert "[task start]" in result.stdout or "[inspect complete]" in result.stdout
    assert "completed" in result.stdout
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
            "a\nok\n"
            "a\nrelease ok\n"
        ),
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Clarification required" in result.stdout
    assert "plan_approved" in result.stdout
    assert "completed" in result.stdout


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


def test_interactive_reject_plan_stops(tmp_path: Path) -> None:
    target = tmp_path / "reject-plan"
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
        input="a\nspec ok\nr\nrework\n",
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "plan_rejected" in result.stdout
