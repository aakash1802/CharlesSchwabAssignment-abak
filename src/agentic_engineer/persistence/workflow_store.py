"""Requirement workflow state persistence."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.models.common import utc_now
from agentic_engineer.models.workflow import RequirementWorkflowState
from agentic_engineer.persistence.json_store import JsonStore


class WorkflowStore:
    def __init__(self, agentic_dir: Path) -> None:
        self._workflows = agentic_dir / "workflows"
        self._workflows.mkdir(parents=True, exist_ok=True)

    def workflow_dir(self, workflow_id: str) -> Path:
        path = self._workflows / workflow_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, state: RequirementWorkflowState) -> Path:
        state = state.model_copy(update={"updated_at": utc_now()})
        directory = self.workflow_dir(state.workflow_id)
        store = JsonStore(directory)
        return store.write_model("state.json", state)

    def load(self, workflow_id: str) -> RequirementWorkflowState:
        store = JsonStore(self.workflow_dir(workflow_id))
        return store.read_model("state.json", RequirementWorkflowState)
