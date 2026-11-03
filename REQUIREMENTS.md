# Requirements

Normative brief for the **Agentic Engineer** prototype. Statements below supersede the earlier generic scaffold where they conflict. Items still undecided stay under Open questions.

## Status

Captured from the Master Build Prompt (Phase 0). Architecture approved. **Current delivery boundary: Phase 6** (demo / packaging). Spec/plan/runbook: [docs/phase6/](docs/phase6/). Phase 5 substrate: [docs/phase5/](docs/phase5/). See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## Problem statement

Build a working prototype of a **standalone agentic software-engineering CLI** that converts natural-language requirements into reviewable engineering outcomes for **independent target projects**. The CLI must demonstrate controlled, stateful, dependency-aware agentic execution (not a thin chain of unstructured LLM calls).

The CLI is the product. Phase 6 complete demo target is the sibling project `../abassign1` (FastAPI ShareApp); it must not live inside this repository.

## Source statements

| Id | Statement |
| --- | --- |
| R1 | Build a working prototype of an agentic software engineering CLI. |
| R2 | The CLI transforms a natural-language requirement into a reviewable engineering outcome for a target project. |
| R3 | The CLI uses an agentic execution model with specialized agents and LangGraph orchestration. |
| R4 | The CLI demonstrates requirement understanding, including ambiguity and missing information. |
| R5 | The CLI demonstrates task decomposition into an explicit dependency graph. |
| R6 | The CLI demonstrates multi-step, dependency-aware execution (sequential and parallel where appropriate). |
| R7 | The CLI generates or modifies application code/tests/docs and records validation results. |
| R8 | Autonomy is controlled: human approvals, deterministic governance, bounded retries, safe-stop, auditability. |
| R9 | The CLI and each target application are separate projects; the target must not depend on the CLI at runtime. |
| R10 | All target file operations go through a Workspace abstraction with isolation and path safety. |
| R11 | Project-specific workflow state lives under the target’s `.agentic/`; global CLI config holds credentials/defaults only. |
| R12 | The CLI must be capable of greenfield, brownfield, and ambiguous-requirement workflows; Phase 6 demo target is sibling `../abassign1` (see [docs/phase6/DEMO.md](docs/phase6/DEMO.md)). |
| R13 | The CLI must write human-readable Markdown artifacts for review (at least specification and plan when those phases exist) and a human-readable summary after each completed workflow phase, in addition to machine-readable JSON under `.agentic/`. |

## Users and context

| Question | Answer |
| --- | --- |
| Who uses the result? | A technical reviewer / human operator of the CLI (R2, R8). |
| What job does it do? | Drive an engineering workflow on a target project from requirement to reportable outcome (R2–R8). |
| What inputs does it receive? | A target project path and a natural-language requirement string (and later approval decisions) (R2). |
| What outputs must it produce? | Spec, plan/graph, code/test/doc changes in the target, approvals history, audit trail, metrics (where data exists), final report, plus human-readable Markdown copies/summaries for reviewer inspection (R2, R7, R8, R13). |

## In scope

- Installable Agentic Engineer CLI (this repository) (R1, R9).
- Workspace isolation and `.agentic/` persistence (R10, R11).
- Requirement analysis, specification, approvals (R4, R8).
- Task planning, dependency validation, LangGraph execution (R3, R5, R6).
- Developer/testing/failure-analysis loop with bounded retries (R7, R8).
- Audit events, derived metrics, final report (R8).
- Human-readable Markdown artifacts for spec/plan (and later phases) plus a phase summary after each completed workflow phase (R13).

## Out of scope (now)

- Embedding demo target application source inside this CLI repository (target is `../abassign1` only).
- Production multi-tenant SaaS, web dashboard, K8s, Redis, Postgres, vector DBs.
- CrewAI/AutoGen or a second custom DAG engine beside LangGraph.
- Embedding any target application inside the CLI repository (R9).
- Unrestricted shell access or LLM self-approval (R8, R10).
- Features deferred in [ARCHITECTURE.md](ARCHITECTURE.md) §2 “Deferred”.

## Constraints

| Constraint | Detail |
| --- | --- |
| Language / platform | Python 3.11+; Typer; Pydantic; LangGraph; Pytest (proposed — confirm in ADR-003). |
| Time | Roughly 5–6 hours; prefer working vertical slice over breadth. |
| Secrets | Never commit API keys or tokens. |
| Separation | Target must not import CLI; CLI must not treat itself as a target (R9, R10). |
| Charles Schwab API | Not required by this brief. |

## Acceptance criteria

- [ ] AC1. Given a target path and requirement, when the CLI runs to a terminal state, then a reviewer can inspect a coherent engineering outcome (spec/plan/changes/report as applicable) without needing to parse JSON alone (R1, R2, R13).
- [ ] AC1b. After each completed workflow phase, a human-readable Markdown summary exists under the target `.agentic/` tree; when a specification or plan is produced, a Markdown form of that artifact is also written (R13).
- [ ] AC2. The outcome records how the requirement was understood, including ambiguities or clarifications when present (R4).
- [ ] AC3. The outcome includes a task decomposition with explicit dependencies (R5).
- [ ] AC4. Execution shows multiple steps and respects dependencies; independent tasks may run in parallel (R6).
- [ ] AC5. Generated or modified outputs are validated (e.g. tests) and the validation result is recorded (R7).
- [ ] AC6. A reviewer can follow one path from requirement through understanding, planning, execution, validation, and report under visible control bounds (approvals, retry limits, or safe-stop) (R3, R8).
- [ ] AC7. A target project initialized or modified by the CLI runs without depending on the CLI package (R9).
- [ ] AC8. Workspace operations reject CLI self-targeting and path escapes; two targets do not share workflow metadata (R10, R11).

## Assumptions

- Input requirement is plain text via CLI flag (R2).
- “Reviewable” includes JSON under `.agentic/`, human-readable Markdown under `.agentic/readable/`, plus `agentic report` when available (R2, R8, R13).
- Phase summaries are Markdown snapshots of that phase’s outcome (analysis, clarification, specification, approval, and later plan/execution/report phases) (R13).
- Default max automatic retries per task is 2 unless configuration overrides (R8).
- Fixture/temp targets remain valid for automated tests; Phase 6 demo uses `../abassign1` (R12).

## Open questions

- [ ] Confirm ADRs in [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) (especially CLI-only repo, stack, simplified replan).
- [x] Real LLM for live runs: **Anthropic** via `AGENTIC_LLM_PROVIDER=anthropic` (Phase 2). See [docs/phase2/LLM_CONFIGURATION.md](docs/phase2/LLM_CONFIGURATION.md).
- [x] Submission packaging: **complete project at `../abassign1`**; CLI remains installable from this repo only (no embedded target source).
- [x] Whether to rename/move into a physical `workspace/agentic-engineer` folder: **no** (ADR-002).
- [x] Demo target: sibling `../abassign1`, FastAPI, scenarios greenfield + brownfield + ambiguous ([docs/phase6/](docs/phase6/)).
