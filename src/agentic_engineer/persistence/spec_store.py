"""Specification persistence under `.agentic/specifications/`."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.models.specification import Specification
from agentic_engineer.persistence.json_store import JsonStore


class SpecStore:
    def __init__(self, agentic_dir: Path) -> None:
        self._dir = agentic_dir / "specifications"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._store = JsonStore(self._dir)

    def save(self, spec: Specification) -> Path:
        return self._store.write_model(f"{spec.id}.json", spec)

    def load(self, spec_id: str) -> Specification:
        return self._store.read_model(f"{spec_id}.json", Specification)

    def latest(self) -> Specification | None:
        files = sorted(self._dir.glob("spec_*.json"))
        if not files:
            return None
        return self._store.read_model(files[-1].name, Specification)
