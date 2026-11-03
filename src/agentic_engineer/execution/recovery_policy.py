"""Deterministic recovery policy (Python-owned; LLM cannot override budgets)."""

from __future__ import annotations

from agentic_engineer.llm.failures import (
    NON_RETRYABLE_CATEGORIES,
    REDUCE_SCOPE_CATEGORIES,
    FailureCategory,
    normalize_category,
)
from agentic_engineer.models.recovery import (
    RecoveryAttempt,
    RecoveryBudgets,
    RecoveryDecision,
    RecoveryStrategy,
)


def budgets_exhausted(
    *,
    strategy: RecoveryStrategy,
    counts: dict[str, int],
    budgets: RecoveryBudgets,
) -> bool:
    if counts.get("total", 0) >= budgets.max_total_recovery_attempts:
        return True
    if strategy == RecoveryStrategy.RETRY_SAME:
        return counts.get("same", 0) >= budgets.max_same_retries
    if strategy == RecoveryStrategy.RETRY_CORRECTED:
        return counts.get("corrected", 0) >= budgets.max_corrected_retries
    if strategy == RecoveryStrategy.REDUCE_SCOPE:
        return counts.get("scope", 0) >= budgets.max_scope_reductions
    if strategy == RecoveryStrategy.REPLAN:
        return counts.get("replan", 0) >= budgets.max_replans
    return False


def repeated_ineffective_pattern(
    history: list[RecoveryAttempt],
    *,
    category: FailureCategory,
    strategy: RecoveryStrategy,
) -> bool:
    """True when the same strategy already failed for the same category."""
    canon = normalize_category(category)
    for attempt in reversed(history):
        if attempt.outcome in {"pending", "succeeded", "awaiting_approval"}:
            continue
        if (
            normalize_category(attempt.failure_category) == canon
            and attempt.strategy == strategy
            and attempt.outcome in {"failed", "escalated"}
        ):
            return True
        # Only inspect the most recent finished attempt for the same category.
        if normalize_category(attempt.failure_category) == canon:
            break
    # Also: two consecutive identical strategy+category attempts (regardless of
    # outcome marking) means the strategy did not resolve the failure.
    matching = [
        a
        for a in history
        if normalize_category(a.failure_category) == canon and a.strategy == strategy
    ]
    return len(matching) >= 1 and strategy != RecoveryStrategy.ESCALATE


def initial_strategy_for_category(
    category: FailureCategory,
    *,
    prefer_replan: bool = False,
    history: list[RecoveryAttempt] | None = None,
) -> RecoveryStrategy:
    """Map a failure category to the initial recovery strategy."""
    canon = normalize_category(category)
    history = history or []

    if canon in {
        FailureCategory.WORKSPACE_VIOLATION,
        FailureCategory.PERMISSION_FAILURE,
    } or category in {
        FailureCategory.INVALID_FILE_OPERATION,
        FailureCategory.WORKSPACE_SAFETY,
    }:
        return RecoveryStrategy.ESCALATE

    if prefer_replan:
        return RecoveryStrategy.REPLAN

    if canon in {
        FailureCategory.TRANSIENT_PROVIDER,
        FailureCategory.RATE_LIMIT,
    }:
        return RecoveryStrategy.RETRY_SAME

    if canon in {
        FailureCategory.INVALID_STRUCTURED_OUTPUT,
        FailureCategory.SCHEMA_VALIDATION,
    }:
        return RecoveryStrategy.RETRY_CORRECTED

    if canon in REDUCE_SCOPE_CATEGORIES:
        return RecoveryStrategy.REDUCE_SCOPE

    if canon == FailureCategory.DEPENDENCY_FAILURE:
        # Missing packages need an install-then-retest command proposal, not a
        # plan rewrite. Escalate if a corrected install retry already failed.
        prior = [
            a
            for a in history
            if normalize_category(a.failure_category) == canon
        ]
        if any(a.strategy == RecoveryStrategy.RETRY_CORRECTED for a in prior):
            return RecoveryStrategy.ESCALATE
        return RecoveryStrategy.RETRY_CORRECTED

    if canon in {
        FailureCategory.IMPLEMENTATION_ERROR,
        FailureCategory.TEST_FAILURE,
    }:
        # Escalating ladder: corrected → replan → escalate
        prior = [
            a
            for a in history
            if normalize_category(a.failure_category) == canon
        ]
        if any(a.strategy == RecoveryStrategy.REPLAN for a in prior):
            return RecoveryStrategy.ESCALATE
        if any(a.strategy == RecoveryStrategy.RETRY_CORRECTED for a in prior):
            return RecoveryStrategy.REPLAN
        return RecoveryStrategy.RETRY_CORRECTED

    if canon == FailureCategory.UNKNOWN:
        # Bound unknown failures with ordinary/same retry budgets; escalate when
        # those are exhausted (handled by decide_strategy), not on first repeat.
        return RecoveryStrategy.RETRY_SAME

    return RecoveryStrategy.ESCALATE


def escalate_decision(
    *,
    category: FailureCategory,
    explanation: str,
    evidence: list[str],
    rationale: str,
) -> RecoveryDecision:
    return RecoveryDecision(
        strategy=RecoveryStrategy.ESCALATE,
        failure_category=category,
        failure_explanation=explanation,
        evidence=evidence,
        proposed_corrective_action="Request human intervention; preserve workflow state.",
        inputs_must_change=False,
        scope_changes=False,
        dependency_graph_changes=False,
        human_approval_required=True,
        confidence=1.0,
        rationale=rationale,
        llm_may_approve=False,
    )


def build_decision(
    *,
    strategy: RecoveryStrategy,
    category: FailureCategory,
    explanation: str,
    evidence: list[str],
    corrective_action: str,
    rationale: str,
    confidence: float = 1.0,
) -> RecoveryDecision:
    inputs_must_change = strategy in {
        RecoveryStrategy.RETRY_CORRECTED,
        RecoveryStrategy.REDUCE_SCOPE,
        RecoveryStrategy.REPLAN,
    }
    scope_changes = strategy in {
        RecoveryStrategy.REDUCE_SCOPE,
        RecoveryStrategy.REPLAN,
    }
    dependency_graph_changes = strategy in {
        RecoveryStrategy.REDUCE_SCOPE,
        RecoveryStrategy.REPLAN,
    }
    human_approval_required = strategy in {
        RecoveryStrategy.REPLAN,
        RecoveryStrategy.ESCALATE,
    }
    return RecoveryDecision(
        strategy=strategy,
        failure_category=category,
        failure_explanation=explanation,
        evidence=evidence,
        proposed_corrective_action=corrective_action,
        inputs_must_change=inputs_must_change,
        scope_changes=scope_changes,
        dependency_graph_changes=dependency_graph_changes,
        human_approval_required=human_approval_required,
        confidence=confidence,
        rationale=rationale,
        llm_may_approve=False,
    )


def validate_llm_recommendation(
    suggested: RecoveryStrategy | str | None,
    *,
    category: FailureCategory,
    deterministic: RecoveryDecision,
) -> RecoveryDecision:
    """Accept an LLM strategy suggestion only when it is safe and coherent.

    The LLM may recommend a strategy; deterministic validation rejects unsafe
    choices. The LLM can never approve recovery or raise budgets.
    """
    if suggested is None:
        return deterministic
    try:
        strategy = (
            suggested
            if isinstance(suggested, RecoveryStrategy)
            else RecoveryStrategy(str(suggested).lower())
        )
    except ValueError:
        return deterministic.model_copy(
            update={
                "rationale": (
                    f"{deterministic.rationale} "
                    f"(ignored invalid LLM suggestion: {suggested!r})"
                ),
                "llm_may_approve": False,
            }
        )

    # Never allow LLM to override escalate for non-retryable failures.
    if normalize_category(category) in {
        FailureCategory.WORKSPACE_VIOLATION,
        FailureCategory.PERMISSION_FAILURE,
    } or category in NON_RETRYABLE_CATEGORIES:
        if strategy != RecoveryStrategy.ESCALATE:
            return escalate_decision(
                category=category,
                explanation=deterministic.failure_explanation,
                evidence=deterministic.evidence
                + [f"Rejected LLM suggestion {strategy.value} for non-retryable failure"],
                rationale=(
                    "Non-retryable failure must escalate; "
                    f"LLM suggested {strategy.value} and was rejected."
                ),
            )

    # LLM cannot self-approve.
    if strategy == RecoveryStrategy.ESCALATE:
        return escalate_decision(
            category=category,
            explanation=deterministic.failure_explanation,
            evidence=deterministic.evidence + ["LLM agreed escalation"],
            rationale=deterministic.rationale,
        )

    # Allow LLM to choose a stricter action among automatic recoveries, but never
    # let an advisory escalate override a deterministic replan/retry floor when the
    # deterministic path already selected a concrete recovery (LLM cannot force
    # escalation to bypass replan approval gates).
    order = [
        RecoveryStrategy.RETRY_SAME,
        RecoveryStrategy.RETRY_CORRECTED,
        RecoveryStrategy.REDUCE_SCOPE,
        RecoveryStrategy.REPLAN,
        RecoveryStrategy.ESCALATE,
    ]
    if strategy == RecoveryStrategy.ESCALATE and deterministic.strategy != RecoveryStrategy.ESCALATE:
        return deterministic.model_copy(
            update={
                "evidence": deterministic.evidence
                + ["Ignored LLM escalate; deterministic recovery still available"],
                "llm_may_approve": False,
            }
        )
    if order.index(strategy) >= order.index(deterministic.strategy):
        return build_decision(
            strategy=strategy,
            category=category,
            explanation=deterministic.failure_explanation,
            evidence=deterministic.evidence + [f"LLM recommended {strategy.value}"],
            corrective_action=deterministic.proposed_corrective_action,
            rationale=(
                f"{deterministic.rationale} Validated LLM recommendation: {strategy.value}."
            ),
            confidence=min(deterministic.confidence, 0.9),
        )

    # Reject weaker suggestions than the deterministic floor.
    return deterministic.model_copy(
        update={
            "evidence": deterministic.evidence
            + [f"Rejected weaker LLM suggestion {strategy.value}"],
            "rationale": (
                f"{deterministic.rationale} "
                f"Kept deterministic {deterministic.strategy.value} "
                f"(LLM suggested weaker {strategy.value})."
            ),
            "llm_may_approve": False,
        }
    )


def decide_strategy(
    *,
    category: FailureCategory,
    error: str,
    history: list[RecoveryAttempt],
    budgets: RecoveryBudgets,
    prefer_replan: bool = False,
    llm_suggestion: RecoveryStrategy | str | None = None,
    ordinary_retry_count: int = 0,
    max_ordinary_retries: int | None = None,
) -> RecoveryDecision:
    """Produce a RecoveryDecision using deterministic policy + optional LLM hint."""
    canon = normalize_category(category)
    evidence = [
        f"failure_category={canon.value}",
        f"error={error[:500]}",
        f"prior_recovery_attempts={len(history)}",
    ]
    counts = {
        "same": sum(1 for a in history if a.strategy == RecoveryStrategy.RETRY_SAME),
        "corrected": sum(
            1 for a in history if a.strategy == RecoveryStrategy.RETRY_CORRECTED
        ),
        "scope": sum(1 for a in history if a.strategy == RecoveryStrategy.REDUCE_SCOPE),
        "replan": sum(1 for a in history if a.strategy == RecoveryStrategy.REPLAN),
        "escalate": sum(1 for a in history if a.strategy == RecoveryStrategy.ESCALATE),
        "total": len(history),
    }

    if counts["total"] >= budgets.max_total_recovery_attempts:
        return escalate_decision(
            category=canon,
            explanation=error,
            evidence=evidence + ["total recovery budget exhausted"],
            rationale=(
                f"Total recovery budget exhausted "
                f"({counts['total']}/{budgets.max_total_recovery_attempts})."
            ),
        )

    if max_ordinary_retries is not None and ordinary_retry_count >= max_ordinary_retries:
        # Ordinary execution retry budget exhausted → escalate unless replan preferred.
        if prefer_replan and not budgets_exhausted(
            strategy=RecoveryStrategy.REPLAN, counts=counts, budgets=budgets
        ):
            return build_decision(
                strategy=RecoveryStrategy.REPLAN,
                category=canon,
                explanation=error,
                evidence=evidence + ["ordinary retry cap exhausted; prefer replan"],
                corrective_action="Patch plan and invalidate affected downstream tasks.",
                rationale=(
                    f"Ordinary retry cap exhausted "
                    f"({ordinary_retry_count}/{max_ordinary_retries}); material replan."
                ),
            )
        return escalate_decision(
            category=canon,
            explanation=error,
            evidence=evidence + ["ordinary retry cap exhausted"],
            rationale=(
                f"Retry cap exhausted "
                f"(retry_count={ordinary_retry_count}, max={max_ordinary_retries}, "
                f"category={canon.value}): {error}"
            ),
        )

    # Category-specific tighter caps (independent of total ordinary max).
    if canon in {
        FailureCategory.INVALID_STRUCTURED_OUTPUT,
        FailureCategory.SCHEMA_VALIDATION,
    } and ordinary_retry_count >= budgets.max_corrected_retries:
        return escalate_decision(
            category=canon,
            explanation=error,
            evidence=evidence + ["corrected retry budget exhausted"],
            rationale=(
                f"Retry cap exhausted for {canon.value} "
                f"(retry_count={ordinary_retry_count}, "
                f"max={budgets.max_corrected_retries}, "
                f"category={canon.value}): {error}"
            ),
        )
    if canon in REDUCE_SCOPE_CATEGORIES and ordinary_retry_count >= budgets.max_scope_reductions:
        return escalate_decision(
            category=canon,
            explanation=error,
            evidence=evidence + ["scope reduction budget exhausted"],
            rationale=(
                f"Retry cap exhausted for {canon.value} "
                f"(retry_count={ordinary_retry_count}, "
                f"max={budgets.max_scope_reductions}, "
                f"category={canon.value}): {error}"
            ),
        )

    if canon in {
        FailureCategory.WORKSPACE_VIOLATION,
        FailureCategory.PERMISSION_FAILURE,
    } or category in NON_RETRYABLE_CATEGORIES:
        return escalate_decision(
            category=canon if canon != FailureCategory.UNKNOWN else category,
            explanation=error,
            evidence=evidence + ["non-retryable category"],
            rationale=(
                f"Non-retryable {category.value}: {error}. "
                "Safe-stop; human intervention required."
            ),
        )

    strategy = initial_strategy_for_category(
        category, prefer_replan=prefer_replan, history=history
    )

    # Avoid repeating an ineffective strategy without new evidence.
    if repeated_ineffective_pattern(history, category=canon, strategy=strategy):
        if canon == FailureCategory.UNKNOWN:
            # Unknown failures do not invent plan mutations; escalate after
            # same-operation retries stop helping.
            ladder = {
                RecoveryStrategy.RETRY_SAME: RecoveryStrategy.RETRY_SAME,
                RecoveryStrategy.RETRY_CORRECTED: RecoveryStrategy.ESCALATE,
                RecoveryStrategy.REDUCE_SCOPE: RecoveryStrategy.ESCALATE,
                RecoveryStrategy.REPLAN: RecoveryStrategy.ESCALATE,
            }
        else:
            if canon == FailureCategory.DEPENDENCY_FAILURE:
                corrected_next = RecoveryStrategy.ESCALATE
            elif canon in REDUCE_SCOPE_CATEGORIES:
                # Truncation: shrink generation before replan/escalate.
                corrected_next = RecoveryStrategy.REDUCE_SCOPE
            elif canon in {
                FailureCategory.INVALID_STRUCTURED_OUTPUT,
                FailureCategory.SCHEMA_VALIDATION,
            }:
                # Non-size structured failures rarely improve via task splitting.
                corrected_next = RecoveryStrategy.ESCALATE
            else:
                corrected_next = RecoveryStrategy.REPLAN
            # Truncation already tried reduce_scope — further plan rewrites
            # rarely fix token limits; escalate instead of endless replan.
            reduce_next = (
                RecoveryStrategy.ESCALATE
                if canon in REDUCE_SCOPE_CATEGORIES
                else RecoveryStrategy.REPLAN
            )
            ladder = {
                RecoveryStrategy.RETRY_SAME: RecoveryStrategy.RETRY_CORRECTED,
                RecoveryStrategy.RETRY_CORRECTED: corrected_next,
                RecoveryStrategy.REDUCE_SCOPE: reduce_next,
                RecoveryStrategy.REPLAN: RecoveryStrategy.ESCALATE,
            }
        next_strategy = ladder.get(strategy, RecoveryStrategy.ESCALATE)
        if next_strategy == strategy and strategy == RecoveryStrategy.RETRY_SAME:
            # Stay on RETRY_SAME until same/ordinary budgets force escalate below.
            pass
        else:
            strategy = next_strategy
            evidence.append("escalated strategy after repeated ineffective recovery")

    if budgets_exhausted(strategy=strategy, counts=counts, budgets=budgets):
        return escalate_decision(
            category=canon,
            explanation=error,
            evidence=evidence + [f"budget exhausted for {strategy.value}"],
            rationale=(
                f"Recovery budget exhausted for {strategy.value} "
                f"(counts={counts}, budgets={budgets.model_dump()})."
            ),
        )

    if (
        strategy == RecoveryStrategy.RETRY_CORRECTED
        and canon == FailureCategory.DEPENDENCY_FAILURE
    ):
        corrective = (
            "Retry with a corrected command that installs missing dependencies "
            "(e.g. python -m pip install -r requirements.txt or the named package) "
            "then re-runs validation/tests. Human must still approve before run."
        )
    else:
        corrective = {
            RecoveryStrategy.RETRY_SAME: "Re-execute the same operation with original inputs.",
            RecoveryStrategy.RETRY_CORRECTED: (
                "Retry with targeted feedback: include the validation/failure details "
                "and require a corrected structured response."
            ),
            RecoveryStrategy.REDUCE_SCOPE: (
                "Split the task into smaller dependent subtasks or reduce output size."
            ),
            RecoveryStrategy.REPLAN: (
                "Revise affected plan tasks and invalidate only downstream dependents."
            ),
            RecoveryStrategy.ESCALATE: "Stop automatic execution; request human intervention.",
        }[strategy]

    if strategy == RecoveryStrategy.RETRY_SAME and canon == FailureCategory.RATE_LIMIT:
        rationale = (
            f"Rate limited on task; retry with backoff "
            f"({counts['same'] + 1}/{budgets.max_same_retries}): {error}"
        )
    elif strategy == RecoveryStrategy.RETRY_SAME and canon == FailureCategory.TRANSIENT_PROVIDER:
        rationale = (
            f"Transient provider failure: {error}. "
            f"Retry {counts['same'] + 1}/{budgets.max_same_retries} allowed."
        )
    elif strategy == RecoveryStrategy.RETRY_CORRECTED and canon in {
        FailureCategory.INVALID_STRUCTURED_OUTPUT,
        FailureCategory.SCHEMA_VALIDATION,
    }:
        rationale = (
            f"Structured-output failure ({canon.value}); regenerate with correction "
            f"({counts['corrected'] + 1}/{budgets.max_corrected_retries}): {error}"
        )
    elif strategy == RecoveryStrategy.REDUCE_SCOPE:
        if canon in REDUCE_SCOPE_CATEGORIES:
            lead = "Truncated/oversized output; reduce generation scope"
        else:
            lead = (
                f"Repeated {canon.value}; reduce generation scope "
                "(split task / shrink output)"
            )
        rationale = (
            f"{lead} "
            f"({counts['scope'] + 1}/{budgets.max_scope_reductions}). {error}"
        )
    elif strategy == RecoveryStrategy.REPLAN:
        rationale = f"Material replan required for {canon.value}: {error}"
    else:
        rationale = (
            f"Deterministic policy selected {strategy.value} for {canon.value}."
        )

    decision = build_decision(
        strategy=strategy,
        category=canon,
        explanation=error,
        evidence=evidence,
        corrective_action=corrective,
        rationale=rationale,
    )
    return validate_llm_recommendation(
        llm_suggestion, category=canon, deterministic=decision
    )
