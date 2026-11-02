"""Minimal LangGraph for requirement → analyze → (clarify|spec) routing."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from agentic_engineer.graph.nodes_requirement import (
    graph_analyze_node,
    graph_generate_spec_node,
)


class RequirementGraphState(TypedDict, total=False):
    requirement: str
    workflow_id: str
    provider: Any
    analysis: dict[str, Any]
    clarification_answers: list[dict[str, Any]]
    needs_clarification: bool
    specification: dict[str, Any]
    route: str


def _route_after_analyze(
    state: RequirementGraphState,
) -> Literal["generate_spec", "await_clarification"]:
    route = state.get("route", "generate_spec")
    if route == "await_clarification":
        return "await_clarification"
    return "generate_spec"


def build_requirement_graph():
    """
    Build an in-process LangGraph used for routing tests.

    Cross-process CLI persistence uses RequirementWorkflowService (JSON +
    approval records). Full LangGraph checkpointer resume expands in Phase 4.
    """
    graph = StateGraph(RequirementGraphState)
    graph.add_node("analyze", graph_analyze_node)
    graph.add_node("generate_spec", graph_generate_spec_node)
    graph.add_node("await_clarification", lambda state: state)
    graph.add_node("await_approval", lambda state: state)

    graph.set_entry_point("analyze")
    graph.add_conditional_edges(
        "analyze",
        _route_after_analyze,
        {
            "generate_spec": "generate_spec",
            "await_clarification": "await_clarification",
        },
    )
    graph.add_edge("generate_spec", "await_approval")
    graph.add_edge("await_clarification", END)
    graph.add_edge("await_approval", END)
    return graph.compile()
