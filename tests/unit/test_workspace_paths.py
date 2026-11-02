"""Workspace path isolation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_engineer.workspace.paths import (
    WorkspaceIsolationError,
    assert_not_cli_target,
    cli_repository_root,
    contained_path,
    resolve_target_path,
)


def test_resolve_absolute_and_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "proj"
    target.mkdir()
    assert resolve_target_path(target) == target.resolve()
    assert resolve_target_path("proj") == target.resolve()


def test_cli_repository_root_points_at_repo() -> None:
    root = cli_repository_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "agentic_engineer").is_dir()


def test_reject_cli_repo_as_target() -> None:
    root = cli_repository_root()
    with pytest.raises(WorkspaceIsolationError):
        assert_not_cli_target(root)
    with pytest.raises(WorkspaceIsolationError):
        assert_not_cli_target(root / "src")


def test_reject_path_traversal(tmp_path: Path) -> None:
    ws = tmp_path / "target"
    ws.mkdir()
    with pytest.raises(WorkspaceIsolationError):
        contained_path(ws, "../escape.txt")


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target"
    outside = tmp_path / "outside"
    target.mkdir()
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("nope", encoding="utf-8")
    link = target / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(WorkspaceIsolationError):
        contained_path(target, Path("link") / "secret.txt")
