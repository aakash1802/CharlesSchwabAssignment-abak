"""Task Planner agent — approved spec → dependency-aware plan (Phase 3)."""

from __future__ import annotations

import json
import uuid

from agentic_engineer.agents.prompt_loader import load_prompt
from agentic_engineer.llm.base import LLMError, LLMProvider, LLMRequest
from agentic_engineer.llm.mock import MockProvider
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.specification import Specification
from agentic_engineer.models.task import Task


def deterministic_plan(
    *,
    workflow_id: str,
    specification: Specification,
) -> EngineeringPlan:
    """Build a fixture-shaped diamond graph with sequential and parallel edges."""
    title = specification.title or "Approved specification"
    tasks = [
        Task(
            id="t1",
            name="Inspect and baseline",
            description=f"Inspect target context for: {title}",
            depends_on=[],
            agent="architecture",
            acceptance_criteria=[
                "Impact summary recorded",
                "In-scope files identified",
            ],
        ),
        Task(
            id="t2",
            name="Core design note",
            description="Produce a short design note covering main changes",
            depends_on=["t1"],
            agent="architecture",
            acceptance_criteria=["Design note covers in-scope requirements"],
        ),
        Task(
            id="t3",
            name="Implement primary path",
            description="Implement the primary functional path from the specification",
            depends_on=["t2"],
            agent="developer",
            acceptance_criteria=list(specification.acceptance_criteria[:2])
            or ["Primary path implemented"],
        ),
        Task(
            id="t4",
            name="Implement secondary path",
            description="Implement a second independent slice that can proceed in parallel",
            depends_on=["t2"],
            agent="developer",
            acceptance_criteria=[
                "Secondary slice implemented without blocking t3",
            ],
        ),
        Task(
            id="t5",
            name="Add and run tests",
            description="Generate/run focused tests for primary and secondary paths",
            depends_on=["t3", "t4"],
            agent="testing",
            acceptance_criteria=["Tests pass for in-scope behavior"],
        ),
        Task(
            id="t6",
            name="Update documentation",
            description="Document the delivered change for reviewers",
            depends_on=["t3", "t4"],
            agent="documentation",
            acceptance_criteria=["Docs mention the approved scope"],
        ),
    ]
    summary = (
        f"Plan for '{title}': foundation (t1→t2), then parallel feature work "
        f"(t3∥t4), then tests/docs (t5/t6)."
    )
    return EngineeringPlan(
        id=f"plan_{uuid.uuid4().hex[:10]}",
        workflow_id=workflow_id,
        specification_id=specification.id,
        summary=summary,
        tasks=tasks,
    )


def _tasks_from_payload(raw_tasks: list[object]) -> list[Task]:
    tasks: list[Task] = []
    for idx, item in enumerate(raw_tasks):
        if not isinstance(item, dict):
            raise ValueError(f"Task at index {idx} must be an object")
        data = dict(item)
        data.setdefault("id", f"t{idx + 1}")
        data.setdefault("name", data["id"])
        data.setdefault("depends_on", [])
        data.setdefault("agent", "developer")
        data.setdefault("status", "pending")
        tasks.append(Task.model_validate(data))
    return tasks


class TaskPlanner:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider
        self._system = load_prompt("task_planner.txt")

    def plan(
        self,
        *,
        workflow_id: str,
        specification: Specification,
    ) -> EngineeringPlan:
        if isinstance(self._provider, MockProvider) and not self._provider.has_queued_responses:
            return deterministic_plan(
                workflow_id=workflow_id, specification=specification
            )

        payload = {"specification": specification.model_dump(mode="json")}
        request = LLMRequest(
            prompt=json.dumps(payload, indent=2) + "\n\nReturn JSON only.",
            system=self._system,
            response_schema_name="EngineeringPlan",
        )
        try:
            from agentic_engineer.llm.json_extract import extract_json_text

            response = self._provider.complete(request)
            data = json.loads(extract_json_text(response.text))
            if not isinstance(data, dict):
                raise ValueError("Plan payload must be a JSON object")
            tasks = _tasks_from_payload(list(data.get("tasks") or []))
            return EngineeringPlan(
                id=data.get("id") or f"plan_{uuid.uuid4().hex[:10]}",
                workflow_id=workflow_id,
                specification_id=specification.id,
                summary=str(data.get("summary") or f"Plan for {specification.title}"),
                tasks=tasks,
            )
        except (LLMError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise LLMError(f"Task planning failed: {exc}") from exc
