"""CLI init / status invocation tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agentic_engineer.cli.main import app
from agentic_engineer.workspace.paths import cli_repository_root

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_init_and_status_relative(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "proj"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert (tmp_path / "proj" / ".agentic" / "config.json").is_file()

    status = runner.invoke(app, ["status", "proj"])
    assert status.exit_code == 0, status.stdout + status.stderr
    assert "schema_version: 1" in status.stdout
    assert "no active workflow" in status.stdout


def test_init_absolute(tmp_path: Path) -> None:
    target = tmp_path / "abs-proj"
    result = runner.invoke(app, ["init", str(target)])
    assert result.exit_code == 0
    assert target.joinpath(".agentic").is_dir()


def test_init_non_empty_without_force(tmp_path: Path) -> None:
    target = tmp_path / "filled"
    target.mkdir()
    (target / "app.py").write_text("print(1)\n", encoding="utf-8")
    result = runner.invoke(app, ["init", str(target)])
    assert result.exit_code == 2
    forced = runner.invoke(app, ["init", str(target), "--force"])
    assert forced.exit_code == 0
    assert (target / "app.py").read_text(encoding="utf-8") == "print(1)\n"


def test_init_rejects_cli_repo() -> None:
    result = runner.invoke(app, ["init", str(cli_repository_root())])
    assert result.exit_code == 3
    assert "Refusing" in result.stderr or "Refusing" in result.stdout


def test_status_missing_fails(tmp_path: Path) -> None:
    result = runner.invoke(app, ["status", str(tmp_path / "nope")])
    assert result.exit_code == 1
