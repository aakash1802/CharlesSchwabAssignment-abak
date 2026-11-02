"""Requirement Analyzer agent."""

from __future__ import annotations

import json
import re

from agentic_engineer.agents.prompt_loader import load_prompt
from agentic_engineer.llm.base import LLMError, LLMProvider, LLMRequest
from agentic_engineer.llm.mock import MockProvider
from agentic_engineer.models.requirements import ClarificationQuestion, RequirementAnalysis

_VAGUE = re.compile(
    r"\b(improve|better|enhance|secure|security|optimize|make\s+it|something|somehow)\b",
    re.IGNORECASE,
)


def deterministic_analyze(requirement: str) -> RequirementAnalysis:
    """Offline/mock heuristic used when no scripted LLM response is available."""
    text = requirement.strip()
    vague_hits = _VAGUE.findall(text)
    short = len(text) < 48
    ambiguous = bool(vague_hits) or short

    questions: list[ClarificationQuestion] = []
    ambiguities: list[str] = []
    missing: list[str] = []

    if ambiguous:
        ambiguities.append(
            "Requirement is underspecified; concrete behavior is not clear enough to implement safely."
        )
        missing.append("Desired behavior, constraints, and success criteria")
        questions.append(
            ClarificationQuestion(
                id="q1",
                question="What concrete behavior or outcome should change?",
                reason="The requirement does not state an actionable capability.",
                essential=True,
            )
        )
        questions.append(
            ClarificationQuestion(
                id="q2",
                question="What constraints or non-functional needs matter (security, performance, compatibility)?",
                reason="Missing constraints would force unsafe assumptions.",
                essential=True,
            )
        )

    functional = [] if ambiguous else [f"Deliver capability described by: {text}"]
    return RequirementAnalysis(
        original_requirement=text,
        summary=("Ambiguous requirement needing clarification" if ambiguous else text),
        functional_requirements=functional,
        non_functional_requirements=[],
        constraints=[],
        ambiguities=ambiguities,
        missing_information=missing,
        clarification_questions=questions,
        needs_clarification=ambiguous,
        assumptions=[] if ambiguous else ["Proceeding with the requirement text as stated."],
    )


class RequirementAnalyzer:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider
        self._system = load_prompt("requirement_analyzer.txt")

    def analyze(self, requirement: str) -> RequirementAnalysis:
        if isinstance(self._provider, MockProvider) and not self._provider.has_queued_responses:
            return deterministic_analyze(requirement)

        request = LLMRequest(
            prompt=f"Requirement:\n{requirement.strip()}\n\nReturn JSON only.",
            system=self._system,
            response_schema_name="RequirementAnalysis",
        )
        try:
            from agentic_engineer.llm.json_extract import extract_json_text

            response = self._provider.complete(request)
            data = json.loads(extract_json_text(response.text))
            data["original_requirement"] = requirement.strip()
            return RequirementAnalysis.model_validate(data)
        except (LLMError, json.JSONDecodeError, ValueError) as exc:
            raise LLMError(f"Requirement analysis failed: {exc}") from exc
