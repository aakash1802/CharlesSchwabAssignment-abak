"""Append-only audit event log under the workflow directory (Phase 5 path)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from agentic_engineer.models.execution import ExecutionEvent
from agentic_engineer.persistence.json_store import JsonStore

# Architecture / Phase 5 normative name. Legacy Phase 4 filename still readable.
HISTORY_FILE = "execution_history.json"
LEGACY_EVENTS_FILE = "execution_events.json"

EventSink = Callable[[ExecutionEvent], None]


class ExecutionEventLog:
    def __init__(
        self,
        workflow_dir: Path,
        *,
        on_event: EventSink | None = None,
    ) -> None:
        self._dir = workflow_dir
        self._store = JsonStore(workflow_dir)
        self._relative = HISTORY_FILE
        self._on_event = on_event
        workflow_dir.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        event_type: str,
        *,
        message: str = "",
        task_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> ExecutionEvent:
        event = ExecutionEvent(
            event_type=event_type,
            message=message,
            task_id=task_id,
            details=details or {},
        )
        events = self.list_events()
        events.append(event)
        self._store.write_json(
            self._relative,
            {"events": [e.model_dump(mode="json") for e in events]},
        )
        if self._on_event is not None:
            self._on_event(event)
        return event

    def list_events(self) -> list[ExecutionEvent]:
        path = self._store.path_for(self._relative)
        if not path.exists():
            legacy = self._dir / LEGACY_EVENTS_FILE
            if legacy.exists():
                path = legacy
                raw = JsonStore(self._dir).read_json(LEGACY_EVENTS_FILE)
                return [
                    ExecutionEvent.model_validate(item) for item in raw.get("events", [])
                ]
            return []
        raw = self._store.read_json(self._relative)
        return [ExecutionEvent.model_validate(item) for item in raw.get("events", [])]
