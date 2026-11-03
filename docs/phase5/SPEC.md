# Phase 5 Spec — Governance and reliability

Status: **Implemented** (vertical slice) — lead resumed Phase 5 (2026-11-03).

Normative scope for **Phase 5 only**. Builds on Phases 0–4 (workspace, requirement/spec/plan gates, LangGraph execution with command approvals, bounded retries, safe-stop, checkpoints). Does not open Phase 6 (concrete demo apps).

## Purpose

After (or alongside) agentic execution, the CLI must leave an auditable, reviewable engineering outcome: approval lineage, an append-only audit trail, metrics derived only from recorded events, a coherent final report (machine + human-readable), controlled replan when plan mutation is required, a release approval gate before “complete,” and clear recovery narrative without unsafe rollback.

## Sources

| Id | Requirement |
| --- | --- |
| R2 | Transform a natural-language requirement into a reviewable engineering outcome for a target project |
| R3 | Agentic execution with specialized agents and LangGraph orchestration |
| R5 | Task decomposition into an explicit dependency graph |
| R6 | Multi-step, dependency-aware execution |
| R7 | Generate or modify application code/tests/docs and record validation results |
| R8 | Controlled autonomy: human approvals, deterministic governance, bounded retries, safe-stop, auditability |
| R9 | CLI and target are separate; target must not depend on the CLI at runtime |
| R11 | Project-specific workflow state under the target’s `.agentic/`; credentials only in global/CLI config |
| R12 | Capable of greenfield, brownfield, and ambiguous-requirement workflows; concrete demo apps deferred |
| R13 | Human-readable Markdown artifacts for review and a human-readable summary after each completed workflow phase, in addition to JSON under `.agentic/` |

REQUIREMENTS “Users and context” / “In scope” also call for approvals history, audit trail, metrics (where data exists), and final report (R2, R8, R13).

## Lead decisions (resolved)

| Topic | Decision |
| --- | --- |
| Release approval scope | **Success path only** — required before successful terminal complete; not required after safe-stop / failure terminals |
| Replan re-approval UX | **Reuse existing plan gate** (`approve` / `reject` / interactive plan approval) — not a distinct approval kind |
| Recovery / rollback | **Narrow rule:** allowed recovery is LangGraph **checkpoint resume** only (`agentic resume`). File-level revert of target changes is out of scope; any such request must be refused as unsafe |
| On-disk layout | **[ARCHITECTURE.md](../../ARCHITECTURE.md) § persistence sketch is normative** for Phase 5 audit/metrics/reports paths (see Data) |

## In scope

- Full approval history and decision lineage persisted under the target `.agentic/` (e.g. `workflows/workflow_<id>/approvals.json`, `decisions.json`) (R8)
- Append-only audit event stream at `.agentic/workflows/workflow_<id>/execution_history.json` (R8; lead decision / Architecture sketch)
- Metrics snapshot at `.agentic/workflows/workflow_<id>/metrics.json`, **derived from audit events only** — must not invent numbers when data is missing (R8; lead decision)
- `agentic report` (and history view of audit events) producing a coherent summary a reviewer can use without parsing JSON alone (R2, R8, R13)
- Machine-readable report artifacts under `.agentic/reports/`; human-readable report Markdown under `.agentic/readable/` in addition to JSON (R13; lead decision / Architecture sketch)
- Documentation agent beyond Phase 4 stub: app-facing notes and/or contribution to the final report as part of the reviewable outcome (R7, R13). With a live LLM provider, product notes may include README/API docs; MockProvider without queued responses keeps template `docs/AGENTIC_NOTES.md`.
- Simplified dynamic replan: patch plan, invalidate affected downstream tasks, require re-approval via the **existing plan gate UX** when the change is material, then continue under existing execution controls (R5, R6, R8; lead decision)
- Release approval gate before the workflow may mark a **successful** terminal “complete” only — not after safe-stop / failure terminals (R8; lead decision)
- Checkpoint recovery narrative for operators: allowed recovery is `agentic resume` from the LangGraph checkpointer; refuse file-level revert and other unsafe rollback (R8; lead decision)
- Close Phase 4 stubs called out as Phase 5: replan edge, rich docs/report, release gate, complete audit/metrics/`agentic report` (R7, R8, R13)

## Out of scope

- Concrete demo target applications and scenario scripts (Phase 6 / R12 deferred)
- Production multi-tenant SaaS, web dashboard, K8s, Redis, Postgres, vector DBs (REQUIREMENTS out of scope)
- CrewAI/AutoGen or a second DAG engine beside LangGraph (REQUIREMENTS out of scope)
- Unrestricted shell access or LLM self-approval (R8)
- Silent / auto-run of agent-proposed commands (Phase 4 policy remains)
- Re-implementing LLM providers (Phase 2 owns `build_provider()`)
- Fully automatic large-scope replans without human approval (**Assumption** / REQUIREMENTS control bounds)
- Git flow / GitSafety unless the lead explicitly re-enables it (deferred since Phase 4; not required by REQUIREMENTS source table)
- File-level revert of target application changes (restore/delete/reset generated or modified files as “undo”) — refused under the narrow recovery rule (lead decision)

## Preconditions

1. Phases 1–4 vertical slice must be available: init, requirement/spec/plan gates, execution with command approve-before-run, retry cap, safe-stop, checkpoint resume (R3, R8, R10, R11).
2. Lead resumed Phase 5 (2026-11-03) — implementation allowed.

## Behavior

1. Given a workflow that has progressed through requirement, planning, and/or execution actions, the solution must append audit events for each major action to `.agentic/workflows/workflow_<id>/execution_history.json` (at least: requirement submitted, spec/plan generated, approval granted/rejected, task started/finished, files modified, command proposed/approved/rejected/executed, tests recorded, retry, replan, safe-stop, completed) (R8; lead decision).
2. Given stored approval decisions, the solution must retain a human-inspectable history under the workflow directory (Architecture: `approvals.json`, `decisions.json`) that shows what was approved or rejected and in what order (R8).
3. Given audit events for a workflow, when the operator requests a report or history, the solution must present a coherent summary from `execution_history.json` and related `.agentic/` artifacts, write/update `.agentic/workflows/workflow_<id>/metrics.json` only from those events, and when metric inputs are missing must say so rather than fabricate values (R2, R8, R13; lead decision).
4. Given a completed (or safely stopped) workflow phase that produces a final or partial report, the solution must write machine-readable report artifact(s) under `.agentic/reports/` and human-readable Markdown under `.agentic/readable/` (R13; lead decision).
5. Given Failure Analysis (or equivalent) that requires plan mutation, the solution must apply a simplified plan patch, invalidate downstream tasks that depend on changed work, and when the change is material must park at the existing plan-approval gate (`awaiting_plan_approval` / `approve` / `reject` / interactive plan UX) before continuing execution — not a separate approval kind (R5, R6, R8; lead decision).
6. Given bounded retries still in force, replan must not raise `max_task_retries` or bypass command/destructive approval gates (R8).
7. Given execution that has produced a candidate successful outcome and report, the solution must interrupt for a release approval before transitioning to successful terminal complete; the LLM must not write that approval. Safe-stop and failure terminal states must not require release approval (R8; lead decision).
8. Given an interrupted or resumable workflow, when the operator runs `agentic resume`, the solution must restore from the LangGraph checkpointer thread (allowed recovery). Given a request to file-level revert target changes, wipe durable `.agentic/` recovery state, or otherwise undo completed side effects outside resume, the solution must refuse and leave state inspectable (R8; lead decision).
9. Given Documentation work in Phase 5, the solution must record documentation or report contributions as part of the reviewable outcome without adding a runtime dependency on the CLI package in the target (R7, R9, R13).

## Data

| Item | Direction | Path (normative) | Description | Source |
| --- | --- | --- | --- | --- |
| Approval records / lineage | output | `.agentic/workflows/workflow_<id>/approvals.json`, `decisions.json` | Ordered decisions for spec, plan (including material replan), command, destructive, release | R8 |
| Audit events | output | `.agentic/workflows/workflow_<id>/execution_history.json` | Append-only stream for major actions | R8 |
| Metrics snapshot | output | `.agentic/workflows/workflow_<id>/metrics.json` | Counts/rates/latencies computed only from events; gaps stated explicitly | R8 |
| Final / partial report (JSON) | output | `.agentic/reports/` | Machine-readable summary of requirement → outcome | R2, R8 |
| Final / partial report (Markdown) | output | `.agentic/readable/` | Human-readable report view (alongside existing ANALYSIS/SPEC/PLAN/phases) | R13 |
| Plan patch | internal/output | plan artifacts under `.agentic/plans/` + workflow state | Simplified replan delta + invalidated downstream task ids; re-approval via plan gate | R5, R6, R8 |
| Release approval | input | recorded via approval lineage above | Human approve/reject before successful complete only | R8 |
| Phase Markdown | output | `.agentic/readable/phases/<nn>_*.md` | Continue phase summaries for new Phase 5 cohorts | R13 |
| Checkpoints | internal | `.agentic/workflows/workflow_<id>/checkpoints/` | LangGraph checkpointer (resume source of truth) | R8, R11 |

Paths match [ARCHITECTURE.md](../../ARCHITECTURE.md) persistence sketch (lead decision).

## Constraints

- The solution must keep workflow state under the target `.agentic/` using the Architecture sketch paths above; credentials remain outside the target (R11; lead decision).
- The solution must not invent metric values when events are insufficient (R8; REQUIREMENTS “where data exists”).
- The solution must reuse Phase 2 `build_provider()` for any LLM calls (**Assumption** / Phase 2 ownership).
- The solution must preserve Phase 4 command approve-before-run and Python-enforced retry caps (R8).
- The solution must not embed the target in the CLI repo or make the target import the CLI (R9).
- Fixture/temp targets remain sufficient until Phase 6 defines demo apps (R12).
- The solution must treat only LangGraph checkpoint resume as allowed automated recovery; it must not implement file-level revert in Phase 5 (R8; lead decision).

## Acceptance criteria

- [x] AC-P5-1. Given a workflow with at least one approval and one executed (or rejected) command, when the operator inspects approval history, then each decision is visible with enough context to see order and outcome without reading only opaque blobs (R8).
- [x] AC-P5-2. Given a workflow that ran tasks, commands, or safe-stop, when audit/history is inspected, then corresponding major actions appear in `.agentic/workflows/workflow_<id>/execution_history.json` (R8).
- [x] AC-P5-3. Given a set of audit events, when `agentic report` (or equivalent) runs, then the output summarizes the path from requirement through planning/execution/validation using those events, `metrics.json` is derived only from events (or states data insufficient), and report artifacts are under `.agentic/reports/` plus Markdown under `.agentic/readable/` (R2, R8, R13).
- [x] AC-P5-4. Given a reportable terminal or partial outcome, when the report is written, then machine-readable content exists under `.agentic/reports/` and a human-readable Markdown form exists under `.agentic/readable/` (R13).
- [x] AC-P5-5. Given a material plan patch from replan, when the patch is applied, then affected downstream tasks are invalidated and execution does not continue past the replan until a human approval is recorded through the existing plan gate UX (R5, R6, R8).
- [x] AC-P5-6. Given a candidate successful outcome after report generation, when release has not been approved, then the workflow must not enter successful terminal complete; after human release approve, it may. Safe-stop and failure terminals must not require release approval (R8).
- [x] AC-P5-7. Given `agentic resume` on a checkpointed workflow, when invoked, then execution continues from the LangGraph thread without reverting target files. Given a request for file-level revert or wiping durable recovery state, when requested, then the CLI refuses and leaves state inspectable (R8).

## Assumptions

- “Major actions” for the audit stream match the list in Behavior §1; REQUIREMENTS requires auditability but does not enumerate every event type.
- Metrics are computed only from events; the exact metric set may be a subset (success counts, retry counts, durations, approval waits) as long as fabrication is forbidden.
- “Material” replan means any patch that changes task identity, dependencies, or acceptance criteria enough to invalidate downstream work; trivial annotation-only edits may skip re-approval only if still recorded in audit (**Assumption**).
- Documentation agent output may be thin (README/notes + report sections) rather than a full product docs site.
- `agentic history` may be a view over the same audit stream as `agentic report` rather than a separate subsystem.
- Git flow remains disabled unless the lead reopens ADR-014 work.
- Phase 5 does not require live paid LLMs for CI; mock provider remains valid (R12).
- Partial reports after safe-stop/failure may still be written; only the success→complete transition is release-gated (lead decision).
- File-level undo remains deferred with git flow; Phase 5 documents and refuses it rather than offering a partial revert API (lead decision).
- Exact filenames *inside* `.agentic/reports/` (e.g. `report_<workflow_id>.json`) may follow existing id patterns used for `spec_<id>` / `plan_<id>`; the directory itself is normative from Architecture.
- Human-readable final report filename under `readable/` may be `REPORT.md` (latest) to match `ANALYSIS.md` / `SPECIFICATION.md` / `PLAN.md` naming (**Assumption** filling Architecture’s `reports/` + `readable/` dual pattern).

## Open questions

_None blocking._ Lead resumed Phase 5.
