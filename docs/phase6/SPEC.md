# Phase 6 Spec — Demo targets and packaging

Status: **Delivered** (seed + runbook) — lead opened Phase 6 (2026-11-03). Operator live verification remaining.

Normative scope for **Phase 6 only**. Does not reopen Phase 5 governance work except to consume its reportable outcomes when demonstrating end-to-end flows.

## Purpose

Demonstrate the CLI against an agreed independent target application and package a complete demo project for submission review, proving greenfield, brownfield, and ambiguous-requirement capability without embedding targets in the CLI repository or creating a runtime dependency on the CLI.

## Sources

| Id | Requirement |
| --- | --- |
| R1 | Build a working prototype of an agentic software engineering CLI |
| R2 | Transform a natural-language requirement into a reviewable engineering outcome for a target project |
| R9 | CLI and each target application are separate projects; the target must not depend on the CLI at runtime |
| R12 | The CLI must be capable of greenfield, brownfield, and ambiguous-requirement workflows; concrete demo apps for those modes are deferred |
| R13 | Human-readable Markdown artifacts and phase summaries for reviewer inspection, in addition to JSON |

## Lead decisions (resolved)

| Topic | Decision |
| --- | --- |
| Demo target path | Sibling `../abassign1` → `C:\Users\Avita\PycharmProjects\abassign1` (outside this CLI repo) |
| Stack | Python **FastAPI** mini-app (share-link / note style) |
| Scenarios | **All three:** greenfield, brownfield, ambiguous (single target path) |
| Packaging | **Complete project** at `../abassign1` is the Phase 6 deliverable; CLI stays installable from this repo only; no target source in the CLI tree; no `workspace/` rename (ADR-002) |
| Phase open | Lead opened Phase 6 (2026-11-03) |

## In scope

- Define and create a **separate** demo target application at `../abassign1` (R9, R12)
- Scenario coverage: greenfield, brownfield, and ambiguous-requirement workflows (R12)
- Independence check: target runs without depending on the CLI package (R9)
- Demo script / runbook: [DEMO.md](DEMO.md) (R1, R2, R13)
- Packaging: complete project at `../abassign1`; CLI package remains this repository without embedded target source (R1, R9)

## Out of scope

- Embedding any target application source inside the CLI repository (R9)
- Making a target import or depend on the CLI at runtime (R9)
- Production multi-tenant SaaS, web dashboard, or infra services (REQUIREMENTS out of scope)
- Charles Schwab API integration (REQUIREMENTS: not required)
- Replacing Phases 1–5 controls (approvals, workspace isolation, audit/report) with a demo-only shortcut path (R8 via prior phases; R9)
- Moving the CLI into a physical `workspace/agentic-engineer` folder (ADR-002)

## Preconditions

1. Lead explicitly opened Phase 6 (2026-11-03).
2. Phase 4–5 outcomes needed for the demo path are demonstrable (execution, approvals, report/audit).
3. Demo target path, stack, scenarios, and packaging expectations are agreed (see Lead decisions).

## Behavior

1. Given demo target `../abassign1`, when the CLI runs the agreed scenario(s) in [DEMO.md](DEMO.md), the solution must produce a reviewable engineering outcome under the target `.agentic/` Markdown/JSON (and `agentic report` when available) (R2, R9, R13).
2. Given greenfield, brownfield, and ambiguous scenarios, the CLI must be runnable in those modes against `../abassign1` without requiring the target to ship CLI code (R12, R9).
3. Given a target modified or created through the demo, when the target is exercised on its own, it must not require the CLI package at runtime (R9).
4. Given packaging = complete project at `../abassign1`, the CLI repository must remain packagable/installable without including target application source (R1, R9).

## Data

| Item | Direction | Description | Source |
| --- | --- | --- | --- |
| Demo target path | input | `../abassign1` (sibling outside CLI repo) | R9, R12 |
| Scenario requirement text | input | See [DEMO.md](DEMO.md) for each mode | R2, R12 |
| Reviewable artifacts | output | Spec/plan/execution/report Markdown + JSON under target `.agentic/` | R2, R13 |
| Runbook / demo script | output | [DEMO.md](DEMO.md) | R1, R2 |
| Complete project | output | FastAPI app at `../abassign1` | R1, packaging decision |
| CLI package | output | This repo (`pip install -e .`); no target source | R1, R9 |

## Constraints

- Demo target must live outside this repository (R9).
- The CLI must not treat itself as a target (R9; prior Workspace rules).
- Secrets must not be committed (REQUIREMENTS Constraints).

## Acceptance criteria

- [x] AC-P6-1. Given `../abassign1` and the documented scenario requirements, when [DEMO.md](DEMO.md) is followed, then a reviewer can inspect a coherent outcome under the target `.agentic/` without the target depending on the CLI package (R2, R9, R13). *(runbook + independence check shipped; live run is operator-executed)*
- [x] AC-P6-2. Given greenfield, brownfield, and ambiguous scenarios, when each is run per the runbook, then the CLI completes to a documented terminal or gated state appropriate to that mode (R12). *(all three modes documented in DEMO.md)*
- [x] AC-P6-3. Given packaging = complete project at `../abassign1`, when the CLI package is produced from this repo, then it contains the Agentic Engineer CLI and does not embed demo target application source (R1, R9). *(complete project outside CLI tree)*

## Assumptions

- Fixture/temp targets from Phases 1–5 remain valid for automated tests.
- Phase 6 may reuse mock LLM for automated checks and live LLM for a recorded demo.
- A single demo target covers all three scenario modes (lead agreed).
- Seed baseline at `../abassign1` supports brownfield/ambiguous; greenfield uses empty-start or documented reset-to-seed steps in [DEMO.md](DEMO.md).

## Open questions

_None blocking._ Lead opened Phase 6; path, stack, scenarios, and packaging resolved.
