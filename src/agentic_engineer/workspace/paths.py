"""Path resolution and CLI self-target / containment checks."""

from __future__ import annotations

from pathlib import Path

import agentic_engineer


class WorkspaceError(Exception):
    """Base error for workspace operations."""


class WorkspaceIsolationError(WorkspaceError):
    """Target path violates isolation rules."""


class WorkspaceNeedsConfirmation(WorkspaceError):
    """Non-empty target requires explicit confirmation before init."""


def package_root() -> Path:
    """Installed / source root of the `agentic_engineer` package."""
    return Path(agentic_engineer.__file__).resolve().parent


def cli_repository_root() -> Path:
    """
    Best-effort repository root for the CLI project.

    Layout: <repo>/src/agentic_engineer/__init__.py → parents[2] == repo.
    Falls back to the package directory when not running from a src layout.
    """
    pkg = package_root()
    # .../src/agentic_engineer
    if pkg.parent.name == "src":
        return pkg.parent.parent.resolve()
    return pkg.resolve()


def resolve_target_path(path: str | Path) -> Path:
    """Resolve a user-supplied path (absolute or relative to CWD)."""
    return Path(path).expanduser().resolve(strict=False)


def is_same_or_nested(path: Path, root: Path) -> bool:
    """True if `path` is `root` or a descendant of `root` (after resolve)."""
    path_r = path.resolve(strict=False)
    root_r = root.resolve(strict=False)
    if path_r == root_r:
        return True
    try:
        path_r.relative_to(root_r)
        return True
    except ValueError:
        return False


def assert_not_cli_target(target: Path, *, cli_root: Path | None = None) -> None:
    """Refuse targeting the CLI repo or anything nested inside it."""
    root = (cli_root or cli_repository_root()).resolve(strict=False)
    target_r = target.resolve(strict=False)
    if is_same_or_nested(target_r, root):
        raise WorkspaceIsolationError(
            f"Refusing to use CLI repository (or a path inside it) as a target: {target_r}"
        )
    # Also refuse writing into the installed package tree if distinct from repo.
    pkg = package_root()
    if is_same_or_nested(target_r, pkg):
        raise WorkspaceIsolationError(
            f"Refusing to use CLI package directory as a target: {target_r}"
        )


def contained_path(root: Path, relative: str | Path) -> Path:
    """
    Join `relative` under `root` and ensure the resolved path stays inside root.

    Rejects `..` traversal and symlink escapes that resolve outside `root`.
    """
    root_r = root.resolve(strict=False)
    candidate = (root_r / relative).resolve(strict=False)
    if not is_same_or_nested(candidate, root_r):
        raise WorkspaceIsolationError(
            f"Path escapes workspace root {root_r}: {relative!s} → {candidate}"
        )
    return candidate
