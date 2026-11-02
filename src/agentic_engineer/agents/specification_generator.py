"""Specification Generator agent."""

from __future__ import annotations

import json
import uuid

from agentic_engineer.agents.prompt_loader import load_prompt
from agentic_engineer.llm.base import LLMError, LLMProvider, LLMRequest
from agentic_engineer.llm.mock import MockProvider
from agentic_engineer.models.requirements import ClarificationAnswer, RequirementAnalysis
from agentic_engineer.models.specification import Specification


def deterministic_specification(
    *,
    workflow_id: str,
    analysis: RequirementAnalysis,
    answers: list[ClarificationAnswer],
) -> Specification:
    """Build a reviewable spec without an LLM (mock/offline path)."""
    answer_map = {a.question_id: a.answer for a in answers}
    clarified = [
        f"{q.question} → {answer_map[q.id]}"
        for q in analysis.clarification_questions
        if q.id in answer_map
    ]
    functional = list(analysis.functional_requirements)
    if clarified:
        functional.extend(f"Clarified: {item}" for item in clarified)
    if not functional:
        functional = [analysis.original_requirement]

    assumptions = list(analysis.assumptions)
    for q in analysis.clarification_questions:
        if q.id not in answer_map:
            assumptions.append(f"Unanswered clarification deferred: {q.question}")

    return Specification(
        id=f"spec_{uuid.uuid4().hex[:10]}",
        workflow_id=workflow_id,
        title=(analysis.summary[:80] or "Engineering specification"),
        summary=analysis.summary,
        functional_requirements=functional,
        non_functional_requirements=list(analysis.non_functional_requirements),
        acceptance_criteria=[
            "Specification reviewed and approved by a human",
            "Implementation matches listed functional requirements",
            "Out-of-scope items are not implemented without a new approval",
        ],
        assumptions=assumptions,
        constraints=list(analysis.constraints),
        in_scope=functional,
        out_of_scope=["Unrelated refactors", "Infrastructure not implied by the requirement"],
    )


class SpecificationGenerator:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider
        self._system = load_prompt("specification_generator.txt")

    def generate(
        self,
        *,
        workflow_id: str,
        analysis: RequirementAnalysis,
        answers: list[ClarificationAnswer],
    ) -> Specification:
        if isinstance(self._provider, MockProvider) and not self._provider.has_queued_responses:
            return deterministic_specification(
                workflow_id=workflow_id, analysis=analysis, answers=answers
            )

        payload = {
            "analysis": analysis.model_dump(mode="json"),
            "clarification_answers": [a.model_dump(mode="json") for a in answers],
        }
        request = LLMRequest(
            prompt=json.dumps(payload, indent=2) + "\n\nReturn JSON only.",
            system=self._system,
            response_schema_name="Specification",
        )
        try:
            from agentic_engineer.llm.json_extract import extract_json_text

            response = self._provider.complete(request)
            data = json.loads(extract_json_text(response.text))
            return Specification.model_validate(
                {
                    **data,
                    "id": data.get("id") or f"spec_{uuid.uuid4().hex[:10]}",
                    "workflow_id": workflow_id,
                }
            )
        except (LLMError, json.JSONDecodeError, ValueError) as exc:
            raise LLMError(f"Specification generation failed: {exc}") from exc
