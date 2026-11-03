# Phase 6 Plan — Demo targets and packaging

Status: **Delivered** (vertical slice) — lead opened Phase 6. Per [SPEC.md](SPEC.md).

## Goal

Ship a complete FastAPI demo project at `../abassign1`, a reproducible runbook for greenfield / brownfield / ambiguous modes, and clear packaging separation (CLI repo ≠ target tree).

## Lead decisions (locked)

| Topic | Decision |
| --- | --- |
| Target path | `../abassign1` |
| Stack | FastAPI (share-link / note style) |
| Scenarios | Greenfield + brownfield + ambiguous |
| Packaging | Complete project at `../abassign1`; CLI installable from this repo only |

## Work packages

| WP | Deliverable | State |
| --- | --- | --- |
| WP1 | Open Phase 6 docs (SPEC/README/PLAN); resolve open questions | Done |
| WP2 | Create complete FastAPI mini-app at `../abassign1` (no CLI dependency) | Done |
| WP3 | [DEMO.md](DEMO.md) runbook + independence check | Done |
| WP4 | Status/packaging updates in AGENTS, README, REQUIREMENTS, IMPLEMENTATION_PLAN | Done |

## Exit criteria

- AC-P6-1..3 addressable via DEMO.md + sibling project + CLI packaging separation
- Lead can follow DEMO.md against `../abassign1` without target importing `agentic_engineer`
