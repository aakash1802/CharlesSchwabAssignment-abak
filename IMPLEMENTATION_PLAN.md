# Implementation Plan

Phased delivery for the Agentic Engineer CLI prototype. Each phase ends with tests, a short demo of what works, explicit limitations, and a **stop for lead approval**.

**Status:** **Phase 6 in progress** (lead opened 2026-11-03). Spec/plan/runbook: [docs/phase6/](docs/phase6/). Demo target: sibling `../abassign1`. Phase 5 substrate: [docs/phase5/](docs/phase5/).

**Companion docs:** [ARCHITECTURE.md](ARCHITECTURE.md), [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md).

**Note:** Phase 6 packaging = complete project at `../abassign1` (FastAPI ShareApp). CLI remains this repository only (no embedded target source).

### Lead checkpoint (recorded)

- **Intent:** Phase 6 opened (2026-11-03). Implement per `docs/phase6/SPEC.md` and `PLAN.md`; runbook [docs/phase6/DEMO.md](docs/phase6/DEMO.md).
- **Demo target:** `../abassign1`; scenarios greenfield + brownfield + ambiguous.
- **Packaging:** Complete project at `../abassign1`; no `workspace/` rename (ADR-002).
- **Command policy:** Relaxed propose-any-command; mandatory human approve/reject before `CommandRunner` runs (ADR-013 amended).
- **Git flow:** Remains disabled until re-enabled.

---

## Time box guidance (≈5–6 hours)

| Priority | Phases | Intent |
| --- | --- | --- |
| Essential | 0–4 | Architecture, foundation, requirement/spec, plan/graph, LangGraph execution with approvals + retries |
| Important (simplified) | 5 | Audit, metrics-from-events, report, thin replan/rollback story |
| Later | 6 | Demo targets, scenario scripts, packaging polish — define when lead is ready |

If time runs short: finish a **vertical slice** through Phase 4 (fixture/temp targets with mocks) before widening agent sophistication.

---

## Phase 0 — Architecture and plan (current)

### Objective

Lock product boundaries, layers, workflow, and phased scope **without code**.

### Deliverables

- [x] `ARCHITECTURE.md`
- [x] `IMPLEMENTATION_PLAN.md`
- [x] `ARCHITECTURE_DECISIONS.md`
- [x] Lead approval

### Exit criteria

- CLI vs target separation agreed.
- Stack and simplified trade-offs agreed.
- Demo apps explicitly deferred.
- Explicit go/no-go for Phase 1.

### Not in this phase

Installs, CLI package code, target applications, dependencies.

---

## Phase 1 — Foundation

**Status:** Implemented — awaiting lead approval before Phase 2.

### Objective

Installable CLI skeleton with **workspace isolation** and persistence primitives before any agent loop.

### Design intent

Prove path safety and multi-target isolation first. Agents that can write files are worthless without a hard boundary.

### Modules / files (expected)

```text
pyproject.toml
src/agentic_engineer/
  cli/main.py, init.py, … (minimal: init, status stub)
  config/settings.py
  models/common.py
  workspace/workspace.py, paths.py
  persistence/json_store.py
  llm/base.py, mock.py
  logging_setup.py
tests/unit/test_workspace_*.py
tests/unit/test_cli_init.py
tests/unit/test_json_store.py
```

### Implement

- Python 3.11+ project (`agentic` entrypoint via Typer).
- Settings from env (LLM keys optional; mock default in tests).
- Structured logging.
- `Workspace`: resolve paths, init empty/missing, confirm non-empty, `.agentic/` bootstrap, reject CLI self-target / nested-in-CLI, reject traversal and symlink escape.
- Atomic JSON read/write + schema version field.
- LLM `Provider` protocol + `MockProvider`.
- Tests for relative/absolute paths, empty vs existing dir, invalid path, two independent temp targets with separate `.agentic/` data, isolation negatives.

### Demo

```text
agentic init ../target-a
agentic init ../target-b
# show separate .agentic trees; attempt init on CLI repo → error
```

### Limitations after Phase 1

No real agents, no LangGraph, no approvals beyond stubs.

### Exit criteria

Pytest green for workspace + init; lead approval for Phase 2.

---

## Phase 2 — Requirement intelligence

**Status:** Approved.

**Audit package:** [docs/phase2/README.md](docs/phase2/README.md) (delivery report, checklist, reviewer guide, pytest capture, sample `.agentic` artifacts).

### Objective

Requirement → analysis → clarification if needed → specification → human approval interrupt/persistence.

### Modules / files

```text
src/agentic_engineer/
  models/requirements.py, specification.py, approval.py
  agents/requirement_analyzer.py
  agents/specification_generator.py
  agents/prompts/…
  governance/approvals.py
  persistence/spec_store.py
  cli/run.py, approve.py, reject.py, spec.py
  graph/ (minimal nodes: analyze → clarify? → spec → interrupt)
tests/… mocked LLM transcripts for ambiguous vs clear requirements
```

### Implement

- Structured analysis (functional / non-functional / constraints / ambiguities / missing).
- Gate: essential clarification → CLI prompts or recorded Q&A before spec.
- Spec model + persistence under `.agentic/specifications/`.
- Human-readable Markdown under `.agentic/readable/` (latest `ANALYSIS.md` / `SPECIFICATION.md` plus `phases/*.md` after each Phase 2 step) (R13).
- Approval record pending → `agentic approve|reject`.
- Ambiguous-requirement path covered with mock LLM (generic fixture requirement, not a specific product).
- **LLM providers in Phase 2:** `MockProvider` + `AnthropicProvider` via `build_provider()` / env config. See [docs/phase2/LLM_CONFIGURATION.md](docs/phase2/LLM_CONFIGURATION.md).

### Demo

```text
agentic run ../demo-target --requirement "<ambiguous requirement>"
agentic status ../demo-target   # pending clarification or approval
agentic approve ../demo-target
agentic spec ../demo-target
```

### Limitations

No task graph yet; no code generation; no real demo app.

### Exit criteria

- [x] Ambiguity path and approval path tested
- [x] Implementation artifacts published under `docs/phase2/` for audit/review
- [x] Real LLM provider (Anthropic) + mock delivered in Phase 2 (do not re-implement in later phases)
- [x] Lead sign-off on Phase 2 package; Phase 3 resumed

---

## Phase 3 — Planning and dependency graph

**Status:** Implemented — **current delivery boundary.** Test and stabilize; Phases 4+ deferred until lead resumes.

### Objective

Approved spec → task plan with explicit dependencies, validation, parallel identification, plan approval.

Reuse Phase 2 `LLMProvider` / `build_provider()` for the Task Planner — no new LLM client.

### Modules / files

```text
src/agentic_engineer/
  models/task.py, plan.py
  agents/task_planner.py
  graph/dependency.py          # validate, cycles, ready-set, parallel cohorts
  persistence/plan_store.py
  cli/plan.py
tests/unit/test_dependency_validation.py
```

### Implement

- Task model (id, deps, status, agent, criteria, retries, …).
- Deterministic validators (missing refs, cycles, completion rules).
- API to list ready tasks and parallel cohorts.
- Plan persistence + plan approval gate.
- Human-readable `readable/PLAN.md` and a `phases/` summary after plan generation/approval (R13).
- Demo graph with both sequential and parallel edges (fixture-shaped, not app-specific).

### Demo

```text
agentic plan ../demo-target
# print ASCII or Mermaid of graph; show parallel ready tasks
agentic approve ../demo-target  # plan gate
```

### Exit criteria

- [x] Cycle detection and parallel ready-set tests
- [x] Plan persistence + readable `PLAN.md` + plan approval gate
- [x] CLI `agentic plan` + reuse `approve`/`reject` for plan gate
- [ ] Lead approval for Phase 4

### Limitations

Planner may still be mock-driven; no Developer/Testing execution; no LangGraph task fan-out yet.

---

## Phase 4 — Agentic execution (core demo)

**Status:** **Implemented** (vertical slice) — lead review / Phase 5 gate pending. Details in [docs/phase4/](docs/phase4/).

### Objective

LangGraph runs the approved plan: design/inspect → execute tasks (seq/logical-parallel) → test → failure analysis → bounded retry → safe-stop; checkpoint + resume. Every agent-proposed command waits for human approve/reject before run.

### Modules / files

```text
src/agentic_engineer/
  graph/state.py, builder.py, nodes_*.py, routing.py
  agents/architecture.py, developer.py, testing.py, failure_analysis.py
  execution/commands.py
  # git_safety.py — deferred (git flow disabled for now)
  workspace/… (used by all writers)
tests/integration/test_workflow_seq_parallel.py
tests/integration/test_checkpoint_resume.py
tests/integration/test_retry_and_safe_stop.py
```

### Implement

- Typed LangGraph state; nodes for inspect/design, schedule, execute task, sync, test, fail-analyze, docs stub.
- Conditional routing; interrupt already wired for approvals; add destructive-action interrupt if needed.
- Parallel fan-out for ready independent tasks; sync barrier.
- Developer + Testing agents via Workspace + CommandRunner.
- Failure Analysis recommendations; Python enforces max retries (default 2).
- File/SQLite LangGraph checkpointer under `.agentic/workflows/<id>/checkpoints/`.
- `agentic resume` restores thread.
- After each execution phase/node cohort completes, write a human-readable `readable/phases/` summary (R13).

### Demo

Fixture/temp target (mock or live LLM via **existing Phase 2** `build_provider()`): plan executes; one forced failure shows retry then success or safe-stop; kill process mid-run and `resume`.

### Limitations

Documentation agent may be minimal; replanning may be stubbed until Phase 5; **git flow / GitSafety disabled** until lead re-enables; logical parallel only (no Send fan-out); commands always approve-before-run; no commitment to a specific product app yet. **Do not re-implement LLM providers here** (Phase 2 owns mock + Anthropic).

### Exit criteria

Integration tests for seq/parallel, retry cap, checkpoint resume; lead approval for Phase 5.

---

## Phase 5 — Governance and reliability

**Status:** **Implemented** (vertical slice) — lead resumed. Normative scope: [docs/phase5/SPEC.md](docs/phase5/SPEC.md).

### Objective

Make outcomes auditable and demonstrably controlled.

### Implement

- Full approval history + decision lineage in `.agentic`.
- Audit event stream for major actions.
- Metrics snapshot derived from events (no invented numbers).
- Simplified dynamic replan: patch plan, invalidate downstream, re-approve if material.
- Checkpoint recovery narrative; refuse unsafe rollback.
- `agentic report` / `history`.
- Human-readable final report Markdown under `.agentic/readable/` (and/or `reports/`) in addition to machine JSON (R13).
- Release approval gate.

### Exit criteria

Report command produces a coherent summary from real events; lead approval before any demo-app work.

---

## Phase 6 — Demo targets and packaging

**Status:** Delivered (seed + runbook) — lead opened 2026-11-03. Normative scope: [docs/phase6/SPEC.md](docs/phase6/SPEC.md). Plan: [docs/phase6/PLAN.md](docs/phase6/PLAN.md). Runbook: [docs/phase6/DEMO.md](docs/phase6/DEMO.md). Operator live runs via [TEST_CHECKLIST.md](TEST_CHECKLIST.md).

### Objective

Demonstrate the CLI against sibling `../abassign1` (FastAPI ShareApp) for greenfield, brownfield, and ambiguous modes; package the **complete project** at that path while keeping the CLI installable from this repo alone.

### Deliverables

- [x] Lead decisions: path `../abassign1`, FastAPI, three scenarios, packaging = complete project there
- [x] Complete seed app at `../abassign1` (no CLI runtime dependency)
- [x] Reviewer runbook [docs/phase6/DEMO.md](docs/phase6/DEMO.md) + independence check
- [x] Status docs updated (AGENTS / README / REQUIREMENTS / this plan)

### Exit criteria

AC-P6-1..3 addressable via DEMO.md + sibling project + CLI/target separation (lead review).

---

## Testing strategy (cross-cutting)

| Area | Phase | Notes |
| --- | --- | --- |
| CLI init / paths | 1 | Absolute, relative, empty, existing, invalid |
| Workspace isolation | 1 | Self-target, traversal, symlink, multi-target |
| Requirement / approval | 2 | Mock LLM (+ Anthropic unit tests with mocked SDK) |
| LLM providers | 2 | **Done** — mock + anthropic; reuse in 3–6 |
| Graph validation | 3 | Cycles, parallel ready-set |
| Orchestration | 4 | Seq, parallel, sync, checkpoint, interrupt (reuse Phase 2 `LLMProvider`) |
| Recovery | 4–5 | Retry bound, safe-stop |
| Target app behavior | 6 | `../abassign1` + DEMO.md |

Paid APIs are not required for CI: use `MockProvider` and fixture transcripts.

---

## Dependency introduction schedule

| Phase | Add |
| --- | --- |
| 1 | typer, pydantic, pytest, (pytest-cov optional) |
| 2 | langgraph; optional `anthropic` extra for live Claude (`pip install -e ".[anthropic]"`) |
| 3–6 | **Do not** add a second LLM client stack — call `build_provider()` / inject `LLMProvider` |
| 4 | Agent execution only; provider SDK already covered in Phase 2 |

No infra services.

---

## Suggested calendar inside a single day

1. Phase 0 review/approve — 20–30 min  
2. Phase 1 — ~60–75 min  
3. Phase 2 — ~45–60 min  
4. Phase 3 — ~45 min  
5. Phase 4 — ~90–120 min (protect this block)  
6. Phase 5 — ~45 min (cut depth if needed)  
7. Phase 6 — only when lead schedules demo-app work  

---

## Stop rule

After each phase: show results, list gaps, **wait for explicit approval** before starting the next phase. Do not silently continue. Phase 6 was opened by the lead (2026-11-03); demo target is `../abassign1`.
