"""Atomic JSON persistence with schema validation on read."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class PersistenceError(Exception):
    """Raised when persisted JSON cannot be read or validated."""


class JsonStore:
    """Read/write JSON documents under a base directory using atomic renames."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)

    def path_for(self, relative: str | Path) -> Path:
        return self.base_dir / relative

    def write_json(self, relative: str | Path, data: dict[str, Any]) -> Path:
        path = self.path_for(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, indent=2, sort_keys=True, default=str)
        self._atomic_write(path, payload)
        return path

    def read_json(self, relative: str | Path) -> dict[str, Any]:
        path = self.path_for(relative)
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except FileNotFoundError as exc:
            raise PersistenceError(f"Missing JSON document: {path}") from exc
        except json.JSONDecodeError as exc:
            raise PersistenceError(f"Invalid JSON in {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise PersistenceError(f"Expected JSON object in {path}")
        return data

    def write_model(self, relative: str | Path, model: BaseModel) -> Path:
        return self.write_json(relative, model.model_dump(mode="json"))

    def read_model(self, relative: str | Path, model_type: type[T]) -> T:
        data = self.read_json(relative)
        try:
            return model_type.model_validate(data)
        except ValidationError as exc:
            raise PersistenceError(f"Schema validation failed for {relative}: {exc}") from exc

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
