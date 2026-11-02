"""Plan persistence under `.agentic/plans/`."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.persistence.json_store import JsonStore


class PlanStore:
    def __init__(self, agentic_dir: Path) -> None:
        self._dir = agentic_dir / "plans"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._store = JsonStore(self._dir)

    def save(self, plan: EngineeringPlan) -> Path:
        return self._store.write_model(f"{plan.id}.json", plan)

    def load(self, plan_id: str) -> EngineeringPlan:
        return self._store.read_model(f"{plan_id}.json", EngineeringPlan)

    def latest(self) -> EngineeringPlan | None:
        files = sorted(self._dir.glob("plan_*.json"))
        if not files:
            return None
        return self._store.read_model(files[-1].name, EngineeringPlan)
