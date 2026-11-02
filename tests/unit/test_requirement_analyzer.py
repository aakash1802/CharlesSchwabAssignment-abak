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


def test_deterministic_detailed_spec_mentioning_security_is_clear() -> None:
    """NFR word 'security' must not force clarification on an otherwise concrete ask."""
    requirement = (
        "Create a URL shortening service with the following functionality:\n"
        "1. Accept a long URL through a REST API.\n"
        "2. Generate a unique short code and return the shortened URL.\n"
        "3. Redirect users to the original URL when they access the short URL.\n"
        "4. Track clicks for each shortened URL.\n"
        "5. Provide an analytics API to retrieve click counts.\n"
        "6. Support URL expiration.\n"
        "7. Support deleting or deactivating shortened URLs.\n"
        "8. Validate URLs and handle invalid, expired, and unknown short codes.\n"
        "\n"
        "Use sensible defaults for technology, architecture, security, and performance. "
        "Prefer a simple, maintainable implementation. Document assumptions rather than "
        "asking for clarification on routine technical choices.\n"
        "\n"
        "No additional business-specific constraints are required at this stage."
    )
    analysis = deterministic_analyze(requirement)
    assert analysis.needs_clarification is False
    assert analysis.clarification_questions == []
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
