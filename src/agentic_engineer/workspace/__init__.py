"""Workspace isolation for target projects."""

from agentic_engineer.workspace.paths import (
    WorkspaceError,
    WorkspaceIsolationError,
    WorkspaceNeedsConfirmation,
    cli_repository_root,
    resolve_target_path,
)
from agentic_engineer.workspace.workspace import Workspace

__all__ = [
    "Workspace",
    "WorkspaceError",
    "WorkspaceIsolationError",
    "WorkspaceNeedsConfirmation",
    "cli_repository_root",
    "resolve_target_path",
]
