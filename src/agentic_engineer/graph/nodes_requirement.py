"""Pure-ish node helpers shared by the workflow service and LangGraph."""

from __future__ import annotations

from typing import Any

from agentic_engineer.agents.requirement_analyzer import RequirementAnalyzer
from agentic_engineer.agents.specification_generator import SpecificationGenerator
from agentic_engineer.llm.base import LLMProvider
from agentic_engineer.models.requirements import ClarificationAnswer, RequirementAnalysis
from agentic_engineer.models.specification import Specification


def run_analyze(requirement: str, provider: LLMProvider) -> RequirementAnalysis:
    return RequirementAnalyzer(provider).analyze(requirement)


def run_generate_spec(
    *,
    workflow_id: str,
    analysis: RequirementAnalysis,
    answers: list[ClarificationAnswer],
    provider: LLMProvider,
) -> Specification:
    return SpecificationGenerator(provider).generate(
        workflow_id=workflow_id,
        analysis=analysis,
        answers=answers,
    )


def route_after_analysis(analysis: RequirementAnalysis) -> str:
    if analysis.needs_clarification and any(
        q.essential for q in analysis.clarification_questions
    ):
        return "await_clarification"
    return "generate_spec"


def graph_analyze_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: analyze requirement from state."""
    provider: LLMProvider = state["provider"]
    analysis = run_analyze(state["requirement"], provider)
    return {
        "analysis": analysis.model_dump(mode="json"),
        "needs_clarification": analysis.needs_clarification,
        "route": route_after_analysis(analysis),
    }


def graph_generate_spec_node(state: dict[str, Any]) -> dict[str, Any]:
    provider: LLMProvider = state["provider"]
    analysis = RequirementAnalysis.model_validate(state["analysis"])
    answers = [
        ClarificationAnswer.model_validate(item)
        for item in state.get("clarification_answers", [])
    ]
    spec = run_generate_spec(
        workflow_id=state["workflow_id"],
        analysis=analysis,
        answers=answers,
        provider=provider,
    )
    return {
        "specification": spec.model_dump(mode="json"),
        "route": "await_approval",
    }
