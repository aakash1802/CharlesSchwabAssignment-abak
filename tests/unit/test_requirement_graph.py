"""LangGraph routing for requirement analysis."""

from __future__ import annotations

from agentic_engineer.graph.requirement_graph import build_requirement_graph
from agentic_engineer.llm import MockProvider


def test_graph_routes_ambiguous_to_clarification() -> None:
    graph = build_requirement_graph()
    result = graph.invoke(
        {
            "requirement": "Improve security somehow",
            "workflow_id": "workflow_test",
            "provider": MockProvider(),
            "clarification_answers": [],
        }
    )
    assert result["needs_clarification"] is True
    assert result["route"] == "await_clarification"
    assert "specification" not in result or result.get("specification") in (None, {})


def test_graph_routes_clear_to_spec() -> None:
    graph = build_requirement_graph()
    result = graph.invoke(
        {
            "requirement": (
                "Add a readiness probe endpoint returning JSON with status ready"
            ),
            "workflow_id": "workflow_test2",
            "provider": MockProvider(),
            "clarification_answers": [],
        }
    )
    assert result["route"] == "await_approval"
    assert result["specification"]["functional_requirements"]
