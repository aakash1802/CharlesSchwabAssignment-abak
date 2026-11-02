"""Requirement analyzer tests (deterministic + scripted LLM)."""

from __future__ import annotations

import json

from agentic_engineer.agents.requirement_analyzer import (
    RequirementAnalyzer,
    deterministic_analyze,
)
from agentic_engineer.llm import LLMRequest, MockProvider


def test_deterministic_flags_ambiguous_requirement() -> None:
    analysis = deterministic_analyze("Improve sharing security")
    assert analysis.needs_clarification is True
    assert analysis.clarification_questions
    assert all(q.essential for q in analysis.clarification_questions)


def test_deterministic_clear_requirement() -> None:
    analysis = deterministic_analyze(
        "Add a healthcheck endpoint that returns HTTP 200 and build version"
    )
    assert analysis.needs_clarification is False
    assert analysis.functional_requirements


def test_analyzer_uses_scripted_llm_json() -> None:
    payload = {
        "original_requirement": "x",
        "summary": "Clear ask",
        "functional_requirements": ["Do X"],
        "non_functional_requirements": [],
        "constraints": [],
        "ambiguities": [],
        "missing_information": [],
        "clarification_questions": [],
        "needs_clarification": False,
        "assumptions": ["A1"],
    }
    provider = MockProvider(responses=[json.dumps(payload)])
    analysis = RequirementAnalyzer(provider).analyze("Build feature X with clear acceptance")
    assert analysis.needs_clarification is False
    assert analysis.functional_requirements == ["Do X"]
    assert provider.calls and isinstance(provider.calls[0], LLMRequest)
