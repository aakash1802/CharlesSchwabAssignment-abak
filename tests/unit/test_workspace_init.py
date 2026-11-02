"""Workspace initialization and multi-target isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_engineer.workspace import (
    Workspace,
    WorkspaceError,
    WorkspaceNeedsConfirmation,
)
from agentic_engineer.workspace.paths import cli_repository_root


def test_init_missing_directory(tmp_path: Path) -> None:
    target = tmp_path / "new-app"
    ws = Workspace.init(target)
    assert ws.root == target.resolve()
    assert ws.agentic_dir.is_dir()
    assert ws.config_path.is_file()
    config = ws.load_config()
    assert config.schema_version == 1
    assert (ws.agentic_dir / "workflows").is_dir()


def test_init_empty_directory(tmp_path: Path) -> None:
    target = tmp_path / "empty"
    target.mkdir()
    ws = Workspace.init(target)
    assert ws.config_path.is_file()


def test_init_non_empty_requires_force(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "README.md").write_text("hi", encoding="utf-8")
    with pytest.raises(WorkspaceNeedsConfirmation):
        Workspace.init(target)
    ws = Workspace.init(target, force=True)
    assert ws.config_path.is_file()
    assert (target / "README.md").read_text(encoding="utf-8") == "hi"


def test_two_targets_isolated_metadata(tmp_path: Path) -> None:
    a = Workspace.init(tmp_path / "a")
    b = Workspace.init(tmp_path / "b")
    a.write_text(".agentic/artifacts/a-only.txt", "A")
    b.write_text(".agentic/artifacts/b-only.txt", "B")
    assert (a.agentic_dir / "artifacts" / "a-only.txt").is_file()
    assert not (b.agentic_dir / "artifacts" / "a-only.txt").exists()
    assert (b.agentic_dir / "artifacts" / "b-only.txt").is_file()
    assert not (a.agentic_dir / "artifacts" / "b-only.txt").exists()


def test_write_rejects_traversal(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "safe")
    with pytest.raises(Exception):
        ws.write_text("../outside.txt", "x")


def test_open_uninitialized_fails(tmp_path: Path) -> None:
    target = tmp_path / "bare"
    target.mkdir()
    with pytest.raises(WorkspaceError):
        Workspace.open(target)


def test_cannot_init_cli_repo() -> None:
    from agentic_engineer.workspace.paths import WorkspaceIsolationError

    with pytest.raises(WorkspaceIsolationError):
        Workspace.init(cli_repository_root())
