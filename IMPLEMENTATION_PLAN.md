# Implementation Plan

Phased delivery for the Agentic Engineer CLI prototype. Each phase ends with tests, a short demo of what works, explicit limitations, and a **stop for lead approval**.

**Status:** **Active build through Phase 3** (planning and dependency graph). Phases 4–6 remain planned but deferred until the lead explicitly resumes them.

**Companion docs:** [ARCHITECTURE.md](ARCHITECTURE.md), [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md).

**Note:** Concrete demo target applications and scenario scripts are **deferred** (see Phase 6). Current focus is the CLI through requirement → spec → plan → plan approval.

### Lead checkpoint (recorded)

- **Intent:** Implement and stabilize Phase 3; do not implement Phase 4+ yet.
- **Architecture:** Unchanged. Resuming Phase 3 does not revise ADRs or later-phase design.
- **Resume:** Start Phase 4 only after an explicit lead instruction (e.g. “resume Phase 4”).

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

### Objective

LangGraph runs the approved plan: design/inspect → execute tasks (seq/parallel) → test → failure analysis → bounded retry → safe-stop; checkpoint + resume.

### Modules / files

```text
src/agentic_engineer/
  graph/state.py, builder.py, nodes_*.py, routing.py
  agents/architecture.py, developer.py, testing.py, failure_analysis.py
  execution/commands.py, git_safety.py
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

Documentation agent may be minimal; replanning may be stubbed until Phase 5; no commitment to a specific product app yet. **Do not re-implement LLM providers here** (Phase 2 owns mock + Anthropic).

### Exit criteria

Integration tests for seq/parallel, retry cap, checkpoint resume; lead approval for Phase 5.

---

## Phase 5 — Governance and reliability

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

## Phase 6 — Demo targets and packaging (deferred)

### Objective

Define and validate concrete target application(s) and packaging — **only when the lead opens this phase**.

### Placeholder (to fill later)

- Which target app(s) and stacks
- Greenfield / brownfield / ambiguous scenarios
- Independence check (target does not depend on CLI)
- Demo script and README runbooks

### Exit criteria

Agreed with lead at the time this phase starts.

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
| Target app behavior | 6 | Deferred with demo apps |

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

After each phase: show results, list gaps, **wait for explicit approval** before starting the next phase. Do not silently continue. Do not start demo-app work until Phase 6 is explicitly opened.
