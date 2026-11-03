"""Persist recovery history under `.agentic/workflows/<id>/recovery_history.json`."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.models.recovery import RecoveryAttempt, RecoveryHistory
from agentic_engineer.persistence.json_store import JsonStore

HISTORY_FILE = "recovery_history.json"


class RecoveryHistoryStore:
    def __init__(self, workflow_dir: Path) -> None:
        self._dir = workflow_dir
        self._store = JsonStore(workflow_dir)
        workflow_dir.mkdir(parents=True, exist_ok=True)

    def load(self, workflow_id: str) -> RecoveryHistory:
        path = self._store.path_for(HISTORY_FILE)
        if not path.exists():
            return RecoveryHistory(workflow_id=workflow_id)
        raw = self._store.read_json(HISTORY_FILE)
        try:
            history = RecoveryHistory.model_validate(raw)
        except Exception:  # noqa: BLE001 — tolerate older/partial files
            return RecoveryHistory(workflow_id=workflow_id)
        if not history.workflow_id:
            history.workflow_id = workflow_id
        return history

    def save(self, history: RecoveryHistory) -> Path:
        return self._store.write_json(HISTORY_FILE, history.model_dump_persist())

    def append(self, workflow_id: str, attempt: RecoveryAttempt) -> RecoveryHistory:
        history = self.load(workflow_id)
        history.append(attempt)
        self.save(history)
        return history

    def update(self, history: RecoveryHistory) -> Path:
        return self.save(history)
