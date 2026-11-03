"""Failure Analysis agent — recommend retry, replan, or stop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentic_engineer.config.settings import get_settings
from agentic_engineer.llm.base import LLMProvider
from agentic_engineer.llm.failures import (
    NON_RETRYABLE_CATEGORIES,
    REDUCE_SCOPE_CATEGORIES,
    FailureCategory,
    classify_from_message,
)
from agentic_engineer.models.execution import FailureRecommendation
from agentic_engineer.models.task import Task


@dataclass(frozen=True)
class FailureAnalysisResult:
    recommendation: FailureRecommendation
    reason: str
    replan_stub: bool = False
    plan_patch: dict[str, Any] = field(default_factory=dict)
    failure_category: FailureCategory | None = None


class FailureAnalysisAgent:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def analyze(
        self,
        *,
        task: Task,
        error: str,
        max_retries: int | None = None,
        prefer_replan: bool = False,
        failure_category: FailureCategory | str | None = None,
    ) -> FailureAnalysisResult:
        _ = self._provider
        cap = max_retries if max_retries is not None else get_settings().max_task_retries
        category = self._resolve_category(error, failure_category)

        if category in NON_RETRYABLE_CATEGORIES:
            return FailureAnalysisResult(
                recommendation="stop",
                reason=(
                    f"Non-retryable {category.value} on {task.id}: {error}. "
                    "Safe-stop; human intervention required."
                ),
                failure_category=category,
            )

        # Structured-output / truncation retries are bounded more tightly than
        # generic transient failures so we do not burn the full cap on the same
        # oversized free-form JSON request.
        structured_cap = min(cap, int(getattr(get_settings(), "max_structured_retries", 2)))
        effective_cap = (
            structured_cap
            if category
            in {
                FailureCategory.INVALID_STRUCTURED_OUTPUT,
                FailureCategory.SCHEMA_VALIDATION,
                FailureCategory.TRUNCATED_RESPONSE,
            }
            else cap
        )

        if task.retry_count < effective_cap:
            if category in REDUCE_SCOPE_CATEGORIES:
                note = (
                    f"Truncated/oversized output on {task.id}; retry with reduced "
                    f"generation scope ({task.retry_count + 1}/{effective_cap}). {error}"
                )
            elif category in {
                FailureCategory.INVALID_STRUCTURED_OUTPUT,
                FailureCategory.SCHEMA_VALIDATION,
            }:
                note = (
                    f"Structured-output failure on {task.id} "
                    f"({category.value}); regenerate "
                    f"({task.retry_count + 1}/{effective_cap}): {error}"
                )
            elif category == FailureCategory.RATE_LIMIT:
                note = (
                    f"Rate limited on {task.id}; retry with backoff "
                    f"({task.retry_count + 1}/{effective_cap}): {error}"
                )
            elif category == FailureCategory.TRANSIENT_PROVIDER:
                note = (
                    f"Transient provider failure on {task.id}: {error}. "
                    f"Retry {task.retry_count + 1}/{effective_cap} allowed."
                )
            else:
                note = (
                    f"Implementation failure on {task.id}: {error}. "
                    f"Retry {task.retry_count + 1}/{effective_cap} allowed."
                )
            return FailureAnalysisResult(
                recommendation="retry",
                reason=note,
                failure_category=category,
            )

        if prefer_replan:
            patch = {
                "failed_task_id": task.id,
                "invalidate_downstream": True,
                "note": (
                    f"Material replan after retry cap on {task.id}: {error}"
                ),
                "failure_category": category.value,
            }
            return FailureAnalysisResult(
                recommendation="replan",
                reason=(
                    f"Retry cap exhausted for {task.id}; material replan required. {error}"
                ),
                replan_stub=False,
                plan_patch=patch,
                failure_category=category,
            )
        return FailureAnalysisResult(
            recommendation="stop",
            reason=(
                f"Retry cap exhausted for {task.id} "
                f"(retry_count={task.retry_count}, max={effective_cap}, "
                f"category={category.value}): {error}"
            ),
            replan_stub=False,
            failure_category=category,
        )

    @staticmethod
    def _resolve_category(
        error: str,
        failure_category: FailureCategory | str | None,
    ) -> FailureCategory:
        if isinstance(failure_category, FailureCategory):
            return failure_category
        if isinstance(failure_category, str) and failure_category:
            try:
                return FailureCategory(failure_category)
            except ValueError:
                pass
        return classify_from_message(error)
