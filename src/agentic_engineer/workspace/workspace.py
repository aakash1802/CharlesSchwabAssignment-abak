"""Workspace abstraction — sole entry for target filesystem access."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from agentic_engineer.models.common import AgenticProjectConfig, utc_now
from agentic_engineer.persistence.json_store import JsonStore
from agentic_engineer.workspace.paths import (
    WorkspaceError,
    WorkspaceNeedsConfirmation,
    assert_not_cli_target,
    contained_path,
    resolve_target_path,
)

logger = logging.getLogger(__name__)

AGENTIC_DIRNAME = ".agentic"
CONFIG_FILENAME = "config.json"


def _is_effectively_empty(path: Path) -> bool:
    """True if path does not exist or contains only ignorable entries."""
    if not path.exists():
        return True
    if not path.is_dir():
        return False
    ignorable = {".git", ".DS_Store", "Thumbs.db"}
    for child in path.iterdir():
        if child.name in ignorable:
            continue
        return False
    return True


@dataclass(frozen=True)
class Workspace:
    """Resolved target project root with scoped helpers."""

    root: Path

    @property
    def agentic_dir(self) -> Path:
        return self.root / AGENTIC_DIRNAME

    @property
    def config_path(self) -> Path:
        return self.agentic_dir / CONFIG_FILENAME

    @classmethod
    def open(cls, path: str | Path) -> Workspace:
        """Open an existing initialized workspace (must contain `.agentic/`)."""
        root = resolve_target_path(path)
        assert_not_cli_target(root)
        if not root.is_dir():
            raise WorkspaceError(f"Target path is not a directory: {root}")
        ws = cls(root=root)
        if not ws.agentic_dir.is_dir():
            raise WorkspaceError(
                f"Target is not initialized (missing {AGENTIC_DIRNAME}/): {root}"
            )
        return ws

    @classmethod
    def init(
        cls,
        path: str | Path,
        *,
        force: bool = False,
    ) -> Workspace:
        """
        Initialize a target directory and create `.agentic/`.

        - Creates the directory if missing.
        - Empty (or only-ignorable) dirs: initialize without confirmation.
        - Non-empty dirs: require `force=True` (CLI `--force` / `--yes`).
        - Idempotent if already initialized: refreshes `updated_at` on config.
        """
        root = resolve_target_path(path)
        assert_not_cli_target(root)

        if root.exists() and not root.is_dir():
            raise WorkspaceError(f"Target path exists and is not a directory: {root}")

        if root.exists() and not _is_effectively_empty(root):
            already = (root / AGENTIC_DIRNAME).is_dir()
            if not already and not force:
                raise WorkspaceNeedsConfirmation(
                    f"Target directory is not empty: {root}. "
                    "Re-run with --force to initialize anyway."
                )

        root.mkdir(parents=True, exist_ok=True)
        ws = cls(root=root)
        ws._ensure_agentic_layout()
        logger.info("workspace_initialized", extra={"root": str(ws.root)})
        return ws

    def _ensure_agentic_layout(self) -> None:
        self.agentic_dir.mkdir(parents=True, exist_ok=True)
        for name in (
            "specifications",
            "plans",
            "workflows",
            "artifacts",
            "reports",
        ):
            (self.agentic_dir / name).mkdir(exist_ok=True)

        store = JsonStore(self.agentic_dir)
        if self.config_path.exists():
            config = store.read_model(CONFIG_FILENAME, AgenticProjectConfig)
            config = config.model_copy(update={"updated_at": utc_now()})
        else:
            config = AgenticProjectConfig()
        store.write_model(CONFIG_FILENAME, config)

    def resolve(self, relative: str | Path) -> Path:
        """Resolve a path relative to the workspace; reject escapes."""
        return contained_path(self.root, relative)

    def read_text(self, relative: str | Path, *, encoding: str = "utf-8") -> str:
        path = self.resolve(relative)
        return path.read_text(encoding=encoding)

    def write_text(
        self,
        relative: str | Path,
        content: str,
        *,
        encoding: str = "utf-8",
        create_parents: bool = True,
    ) -> Path:
        path = self.resolve(relative)
        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return path

    def load_config(self) -> AgenticProjectConfig:
        return JsonStore(self.agentic_dir).read_model(
            CONFIG_FILENAME, AgenticProjectConfig
        )
