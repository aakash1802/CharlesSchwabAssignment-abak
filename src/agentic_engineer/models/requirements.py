"""Requirement analysis models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    reason: str
    essential: bool = True


class RequirementAnalysis(BaseModel):
    """Structured reading of a natural-language requirement."""

    original_requirement: str
    summary: str
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    needs_clarification: bool = False
    assumptions: list[str] = Field(default_factory=list)


class ClarificationAnswer(BaseModel):
    question_id: str
    answer: str
