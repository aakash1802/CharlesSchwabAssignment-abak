# Phase 4 Spec — Agentic execution

Status: **Implemented** (vertical slice; lead review pending) — decisions below recorded 2026-11-03

Normative scope for **Phase 4 only**. Builds on Phases 0–3 (workspace, requirement/spec gates, approved dependency graph). Does not reopen Phase 5 (full audit metrics, dynamic replan, release gate) or Phase 6 (demo apps).

## Purpose

After plan approval, the CLI must execute the approved task graph with LangGraph: inspect/design, schedule ready tasks (sequential and parallel with sync), implement and test via specialized agents under Workspace and command policy, apply bounded retries and safe-stop, checkpoint for resume, and leave human-readable phase summaries for review.

## Sources

| Id | Requirement |
| --- | --- |
| R3 | Agentic execution with specialized agents and LangGraph orchestration |
| R6 | Multi-step, dependency-aware execution (sequential and parallel where appropriate) |
| R7 | Generate or modify application code/tests/docs and record validation results |
| R8 | Controlled autonomy: human approvals, deterministic governance, bounded retries, safe-stop, auditability |
| R9 | CLI and target are separate projects; target must not depend on the CLI |
| R10 | All target file operations go through Workspace with isolation and path safety |
| R11 | Workflow state under target `.agentic/`; credentials only in global/CLI config |
| R12 | Capable of greenfield/brownfield/ambiguous flows; concrete demo apps deferred |
| R13 | Human-readable Markdown after each completed workflow phase, in addition to JSON |

Architecture constraints used as **Assumptions** where REQUIREMENTS.md is silent: ADR-003 (stack), ADR-006 (Python owns transitions/caps), ADR-008 (dual persistence), ADR-009 (interrupt + approve/reject), ADR-010 (retry cap default 2). ADR-013 is **amended for Phase 4** (relaxed propose-any-command + mandatory human approve before run). ADR-014 (git safety) remains **deferred**.

## Lead decisions (resolved)

| Topic | Decision |
| --- | --- |
| Phase 4 start | Lead explicitly resumed Phase 4 — implementation allowed |
| Command policy | **Relaxed:** agent may propose any argv/shell string; `CommandRunner` must **never** execute silently — always interrupt for approve/reject first |
| Destructive-action interrupt | **Required** in the first vertical slice |
| Parallelism | **Logical parallel:** sequential scheduler that marks parallel cohorts; demo must still show independent readiness (not LangGraph Send fan-out required) |
| Git flow | **Deferred** (unchanged) |

## In scope

- LangGraph execution of an **approved** plan/task graph (R3, R6)
- Architecture/Design inspect node (simplified inspect + design note allowed) (R3, R12)
- Developer agent: create/modify files only via Workspace (R7, R9, R10)
- Testing agent: generate and/or propose commands; run only after human approve via CommandRunner; record results (R7, R8)
- Failure Analysis agent: recommend retry / stop (replan may be stubbed) (R8)
- Ready-set scheduling: sequential execution with **logical** parallel cohorts + sync barrier semantics (R6)
- Bounded automatic retries per task; Python-enforced cap (default 2) (R8)
- Safe-stop on exhausted retries, isolation failure, rejected/denied high-impact action (R8)
- Destructive / high-impact action interrupt in the first slice (R8)
- Every CommandRunner invocation gated by human approve/reject (R8; lead decision)
- LangGraph checkpointer under `.agentic/workflows/<id>/checkpoints/` and `agentic resume` (R3, R8, R11)
- Human-readable `readable/phases/` summaries after execution cohorts (R13)
- Reuse Phase 2 `build_provider()` / `LLMProvider` — no second LLM subsystem (**Assumption**)

## Out of scope

- **Git flow / GitSafety** (dirty-tree gating, `agentic/<workflow-id>` branch/commit checkpoints, any git mutate/reset) — disabled for now; resume later under ADR-014
- True concurrent LangGraph Send/map-reduce fan-out (logical parallel is sufficient)
- Silent / auto-run of agent-proposed commands without human approve
- Full dynamic replan with plan patch + re-approval (Phase 5)
- Complete audit metrics (success rate, MTTR, e2e latency dashboards) and `agentic report` polish (Phase 5)
- Release approval gate (Phase 5)
- Rich Documentation agent / final product report (Phase 5; stub only here)
- Concrete demo target applications and scenario scripts (Phase 6 / R12 deferred)
- Second DAG engine beside LangGraph; LLM self-approval (R8, R9)
- Re-implementing mock/Anthropic providers
- Changing Phase 2/3 gate semantics except wiring plan-approved → execute

## Preconditions

1. Target must be initialized with `.agentic/` (R11).
2. Workflow must have an approved specification and an approved, validated plan (Phases 2–3).
3. Task graph must pass deterministic validation (no cycles, deps resolvable) before any task side effect (R6; **Assumption** from Phase 3 validators).

## Behavior

1. Given an approved plan, when execution starts, the solution must load plan/tasks into LangGraph typed state and must not mutate files outside the Workspace root (R3, R10).
2. Given a brownfield or existing tree, when execution begins, the solution must run an inspect/design step before task side effects (**Assumption** / ADR-016 intent; R12).
3. Given task statuses, the solution must schedule only tasks whose dependencies are `completed`; independent ready tasks must be identifiable as a parallel cohort and may be executed in any order within the cohort without waiting on each other; dependents must wait at a sync barrier (R6; logical parallel).
4. Given a Developer task, the solution must apply file changes only through Workspace APIs and must not import CLI packages into the target (R7, R9, R10).
5. Given a Testing task or any agent-proposed command, the solution must present the argv/shell proposal, interrupt for human approve/reject, and only then run via CommandRunner (fixed cwd under workspace, timeout, captured I/O) and must persist validation evidence (R7, R8; Phase 4 command policy).
6. Given a task failure, the solution must invoke Failure Analysis for a recommendation; automatic retry must not exceed `max_task_retries` (default 2); when the cap is exhausted or recovery is not allowed, the solution must safe-stop and persist state (R8; ADR-010).
7. Given a command or action classified as destructive/high-impact, the solution must interrupt for human approve/reject before proceeding; the LLM must not write the approval decision (R8; ADR-009). Command-run gates satisfy this for command execution.
8. Given an in-progress or interrupted execution, when the operator runs `agentic resume <target>`, the solution must restore from the LangGraph checkpointer thread for that workflow, not from JSON state alone (R3, R8, R11; ADR-008).
9. Given completion of an execution phase/node cohort (inspect, task batch, test, fail-analyze, safe-stop), the solution must write a human-readable Markdown summary under `.agentic/readable/phases/` (R13).
10. Given Failure Analysis that would require plan mutation, Phase 4 may stub replan (record recommendation and safe-stop or no-op) rather than applying a plan patch (**Assumption**; full replan is Phase 5).
11. The solution must not invoke git status/branch/commit/reset as part of Phase 4 execution (**Assumption** — git flow disabled).

## Data

| Item | Direction | Description | Source |
| --- | --- | --- | --- |
| Approved plan / task graph | input | Validated tasks with deps, agents, criteria, retry counters | R5/R6 (Phase 3) |
| LangGraph workflow state | internal | Requirement/spec/plan refs, task statuses, errors, stop reason, thread id | R3 |
| Checkpoints | output | LangGraph checkpointer files under `.agentic/workflows/<id>/checkpoints/` | R11, ADR-008 |
| File diffs / created paths | output | Target application changes via Workspace | R7, R10 |
| Command proposals | internal/output | Proposed argv/shell awaiting human decision | R8 |
| Test / command evidence | output | Captured exit code, stdout/stderr summary, pass/fail in workflow JSON | R7, R8 |
| Approval records | input/output | Spec/plan/destructive **and** command-run gates; existing approve/reject CLI | R8 |
| Phase Markdown | output | `.agentic/readable/phases/<nn>_*.md` after cohorts | R13 |
| Audit events (minimal) | output | At least task start/finish, command proposed/approved/rejected/executed, retry, safe-stop | R8 |

## Constraints

- The solution must use LangGraph `StateGraph` for execution orchestration (R3).
- The solution must treat the task dependency graph as data validated in Python; LangGraph must not become a second ad-hoc DAG validator (R6; **Assumption**).
- The solution must reuse `build_provider()` for any LLM calls (**Assumption** / Phase 2 ownership).
- The solution must enforce `max_task_retries` in Python regardless of LLM recommendation (R8).
- The solution must refuse CLI self-target and path escapes (R10).
- The solution must not execute an agent-proposed command until a human approve record exists for that proposal (R8; lead decision).
- Fixture/temp targets with mock LLM are sufficient to demonstrate Phase 4 (R12).

## Acceptance criteria

- [x] AC-P4-1. Given an approved plan with a sequential dependency chain, when execution runs, then tasks complete in dependency order and dependents do not start before prerequisites are `completed` (R6).
- [x] AC-P4-2. Given an approved plan with two independent ready tasks, when execution runs, then both are marked as the same parallel cohort / independently ready, neither waits on the other, and a dependent task waits until both required deps complete (R6).
- [x] AC-P4-3. Given a Developer task, when it succeeds, then target files changed only under the Workspace root and the target project does not gain a runtime dependency on the CLI package (R7, R9, R10).
- [x] AC-P4-4. Given a Testing step, when a command is proposed, then execution waits for human approve/reject; after approve, CommandRunner evidence (exit code and capture) is recorded in workflow artifacts (R7, R8).
- [x] AC-P4-5. Given a forced task failure with `max_task_retries=2`, when Failure Analysis recommends retry, then at most two automatic retries occur; a further failure results in safe-stop with persisted state (R8).
- [x] AC-P4-6. Given execution interrupted mid-run (process kill or interrupt), when `agentic resume <target>` is invoked, then the workflow continues from the LangGraph checkpoint without redoing completed durable steps incorrectly (R3, R8).
- [x] AC-P4-7. Given an agent-proposed command, when the human rejects it, then CommandRunner must not execute it; when approved, it may run with cwd confined to the workspace and captured I/O (R8).
- [x] AC-P4-8. After inspect, task cohort, test, and safe-stop/completion cohorts, human-readable Markdown phase summaries exist under `.agentic/readable/phases/` (R13).
- [x] AC-P4-9. Integration tests cover seq/logical-parallel, retry cap + safe-stop, checkpoint resume, and command approve/reject gate (R3, R6, R8).

## Assumptions

- Architecture agent may be “deterministic inspect + one LLM design summary” if time-boxed (ADR agent table).
- Developer / Testing / Documentation agents call the configured LLM for file writes, command proposals, and docs when the provider is live (or MockProvider has queued responses). Offline `MockProvider()` without a queue keeps deterministic stubs (`src/generated/{task}.py`, `print('test-ok:…')`, template notes) so fixture tests stay hermetic.
- Documentation product notes / release report were expanded in Phase 5; per-task docs use the same LLM-or-stub pattern.
- Replan edge from Failure Analysis is stubbed (recommend + stop or record only) until Phase 5.
- Default `max_task_retries` remains 2 via existing settings.
- Checkpointer is file-based or SQLite under the workflow directory; JSON `state.json` is a mirror, not the resume source of truth.
- Destructive-action gate covers deletes of trees and broad rewrites; command-run gate covers all CommandRunner invocations.
- GitSafety / ADR-014 remains valid architecture but is out of Phase 4 build scope until re-enabled.
- Command proposals are persisted so `--interactive` and explicit `approve`/`reject` both work (same dual UX as Phase 2–3).

## Open questions

_None blocking._ Remaining optional polish (exact approval record shape for commands) may be decided during implementation without a further lead gate.
