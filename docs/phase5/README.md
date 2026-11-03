# Phase 5 — planning package

**Status:** **Implemented** (vertical slice) — lead resumed Phase 5 (2026-11-03).

**Locked decisions:** release approval on success path only; material replan reuses existing plan gate UX; recovery is checkpoint resume only (file-level revert refused); `.agentic/` audit/metrics/reports paths follow the Architecture persistence sketch.

| Doc | Role |
| --- | --- |
| [SPEC.md](SPEC.md) | Normative Phase 5 behavior and acceptance criteria |
| [PLAN.md](PLAN.md) | Work packages and exit criteria |

Parent references: [IMPLEMENTATION_PLAN.md](../../IMPLEMENTATION_PLAN.md), [REQUIREMENTS.md](../../REQUIREMENTS.md), [docs/phase4/](../phase4/).

Closes Phase 4 stubs: dynamic replan, documentation/report, release gate, full audit/metrics/`agentic report`. Git flow remains deferred unless re-enabled separately.

## Failure recovery decision engine

Task failures route through `fail_analyze` → deterministic `RecoveryDecisionEngine` (with optional Failure Analysis advisory). Strategies: `retry_same`, `retry_corrected`, `reduce_scope`, `replan`, `escalate`. Budgets are Python-enforced (`max_same_retries`, `max_corrected_retries`, `max_scope_reductions`, `max_replans`, `max_total_recovery_attempts`). **Scope-reduction budgets and nesting depth apply across the task lineage** (`t7` → `t7_s1` → `t7_s1_s1`), so nested `_sN` ids cannot reset `(1/N)` forever. Non-size structured-output failures escalate after corrected retries instead of splitting. History persists at `.agentic/workflows/<id>/recovery_history.json` and is checkpointed in LangGraph state. LLM recommendations are validated; the LLM cannot raise budgets or approve recovery. The documentation agent uses structured parse, higher `max_tokens`, and diagnostics under `.agentic/artifacts/diagnostics/`.
