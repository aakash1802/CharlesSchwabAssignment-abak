"""Task planner agent tests (deterministic + scripted LLM)."""

from __future__ import annotations

import json

import pytest

from agentic_engineer.agents.task_planner import TaskPlanner, deterministic_plan
from agentic_engineer.graph.dependency import validate_graph
from agentic_engineer.llm import MockProvider
from agentic_engineer.llm.base import LLMError
from agentic_engineer.models.specification import Specification


def _spec() -> Specification:
    return Specification(
        id="spec_test",
        workflow_id="workflow_test",
        title="Improve sharing security",
        summary="Secure share links",
        functional_requirements=["Expiring signed links"],
        acceptance_criteria=["Links expire", "Public reads still work"],
    )


def test_deterministic_plan_validates_with_parallel_edges() -> None:
    plan = deterministic_plan(workflow_id="workflow_test", specification=_spec())
    result = validate_graph(plan.tasks)
    assert result.ok, result.error_messages
    ids = {t.id for t in plan.tasks}
    assert {"t1", "t2", "t3", "t4", "t5", "t6"} <= ids
    # Parallel pair after t2
    t3 = next(t for t in plan.tasks if t.id == "t3")
    t4 = next(t for t in plan.tasks if t.id == "t4")
    assert t3.depends_on == ["t2"]
    assert t4.depends_on == ["t2"]


def test_planner_mock_uses_deterministic_when_queue_empty() -> None:
    planner = TaskPlanner(MockProvider())
    plan = planner.plan(workflow_id="workflow_test", specification=_spec())
    assert plan.specification_id == "spec_test"
    assert validate_graph(plan.tasks).ok


def test_planner_uses_scripted_llm_json() -> None:
    payload = {
        "summary": "Custom plan",
        "tasks": [
            {
                "id": "a",
                "name": "Root",
                "description": "start",
                "depends_on": [],
                "agent": "architecture",
                "acceptance_criteria": ["done"],
            },
            {
                "id": "b",
                "name": "Child",
                "description": "next",
                "depends_on": ["a"],
                "agent": "developer",
                "acceptance_criteria": ["done"],
            },
        ],
    }
    provider = MockProvider(responses=[json.dumps(payload)])
    plan = TaskPlanner(provider).plan(
        workflow_id="workflow_test", specification=_spec()
    )
    assert plan.summary == "Custom plan"
    assert [t.id for t in plan.tasks] == ["a", "b"]


def test_planner_invalid_json_fails_closed() -> None:
    provider = MockProvider(responses=["not-json-at-all"])
    with pytest.raises(LLMError):
        TaskPlanner(provider).plan(workflow_id="workflow_test", specification=_spec())
