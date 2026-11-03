# Phase 5 Plan — Governance and reliability

Status: **Implemented** (vertical slice) — lead resumed Phase 5. Per [SPEC.md](SPEC.md).

## Goal

Vertical slice: audit (`execution_history.json`) + metrics-from-events + `report`/`history` + thin docs + material replan via existing plan gate + release gate on success only + refuse file-level revert.

## Work packages

| WP | Deliverable | State |
| --- | --- | --- |
| WP1 | Audit history path + metrics derivation + decisions lineage | Done |
| WP2 | `agentic report` / `history` + `reports/` JSON + `readable/REPORT.md` | Done |
| WP3 | Docs agent beyond stub; success path parks at release approval | Done |
| WP4 | Failure Analysis `replan` → plan patch → `awaiting_plan_approval` | Done |
| WP5 | CLI refuse file-level revert; tests for ACs | Done |

## Exit criteria

Phase 5 ACs green under pytest; lead review before Phase 6.
