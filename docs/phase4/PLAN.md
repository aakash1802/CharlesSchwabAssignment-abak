# Phase 4 Plan — Agentic execution

Status: **Implemented** (vertical slice) — lead review / Phase 5 gate pending. Per [SPEC.md](SPEC.md) lead decisions.

Companion: [SPEC.md](SPEC.md). Parent: [IMPLEMENTATION_PLAN.md](../../IMPLEMENTATION_PLAN.md) § Phase 4.

## Goal

Vertical slice: **approved plan → LangGraph execute (seq + logical parallel) → test evidence → bounded retry / safe-stop → checkpoint resume**, with Workspace + **approve-before-run** CommandRunner and phase Markdown (R13).

Time box guidance from parent plan: ~90–120 minutes for a working slice; deepen agents only after orchestration tests are green.

## Lead decisions (locked)

| Topic | Decision |
| --- | --- |
| Command policy | Propose any argv/shell; **always** interrupt for approve/reject before run |
| Destructive interrupt | Required in first slice |
| Parallelism | Logical parallel cohorts (sequential scheduler) |
| Git flow | Deferred |

## Preconditions (already done)

| Item | Location |
| --- | --- |
| Workspace isolation | `workspace/` |
| LLM providers | `llm/` + `build_provider()` |
| Spec + plan gates | Phase 2–3 workflow |
| Task model + dependency validation / ready-set / cohorts | `graph/dependency.py`, `models/task.py`, `models/plan.py` |
| `max_task_retries` setting | `config/settings.py` |
| Requirement LangGraph (no full checkpointer resume) | `graph/requirement_graph.py` |

## Work packages

### WP0 — Wire entry from plan approval

- On plan approve, transition workflow to execution-ready (or auto-start execute in same session when `--interactive`).
- CLI: extend `run` / add `resume`; status shows execution states (`executing`, `awaiting_command_approval`, `awaiting_destructive_approval`, `safe_stopped`, …).
- Do not break Phase 2–3 explicit-gate UX.

### WP1 — Execution toolkit

| Module | Responsibility |
| --- | --- |
| `execution/commands.py` | CommandRunner: accept proposed argv/shell string; **park for approve/reject**; on approve run with cwd=workspace (or approved subdir), timeout, capture stdout/stderr/exit; never silent run |
| Workspace (existing) | Sole file I/O for Developer |

**Disabled for now:** `execution/git_safety.py`.

Deliverable: unit tests for reject-does-not-run, approve-runs-with-capture, cwd containment.

### WP2 — LangGraph execution graph

| Module | Responsibility |
| --- | --- |
| `graph/state.py` | Typed state: plan ref, task statuses, design note, test results, pending command proposal, errors, stop reason, thread id |
| `graph/builder.py` | Build StateGraph; compile with checkpointer |
| `graph/routing.py` | Conditional edges: schedule → execute → sync → test → fail-analyze → retry/stop; command/destructive interrupt |
| `graph/nodes_*.py` | inspect/design, schedule, execute_task, sync, test, fail_analyze, docs_stub |

Rules:

- Ready-set from Phase 3 `dependency.py` drives schedule.
- **Logical parallel:** schedule a cohort of independent ready tasks; run them sequentially in any order; mark cohort in status/artifacts; sync before dependents.
- Checkpointer path: `<target>/.agentic/workflows/<id>/checkpoints/`.
- Persist app mirror JSON separately (ADR-008).

### WP3 — Agents

| Agent | Phase 4 bar |
| --- | --- |
| Architecture | Deterministic inspect + optional LLM design summary |
| Developer | LLM-proposed edits → Workspace write; no direct shell |
| Testing | Propose command (any argv/shell string) → human gate → CommandRunner; record evidence |
| Failure Analysis | Structured recommend `retry` \| `stop` (replan stubbed) |
| Documentation | Stub phase note only |

All LLM calls via injected `LLMProvider` from `build_provider()`.

### WP4 — Governance hooks

- Reuse `governance/approvals.py` for **command-run** and destructive-action interrupts (first slice).
- Python enforces retry cap; ignore LLM attempts to raise it.
- Safe-stop writes durable reason + readable phase summary.
- Minimal append-only execution events (task/command proposed/approved/rejected/executed/retry/safe-stop) for Phase 5 to extend.

### WP5 — CLI + readable artifacts

```text
agentic run <target>                 # continue into execute when plan approved
agentic resume <target>              # LangGraph thread restore
agentic status <target>              # show task statuses / pending command / stop reason
agentic approve / reject <target>    # command-run, destructive, and existing gates
# --interactive: prompt at command/destructive gates in-session
```

R13: write `readable/phases/` after inspect, each sync cohort, test, fail-analyze, safe-stop/complete.

### WP6 — Tests (exit gate)

| Test | Asserts |
| --- | --- |
| `tests/integration/test_workflow_seq_parallel.py` | AC-P4-1, AC-P4-2 (logical parallel) |
| `tests/integration/test_retry_and_safe_stop.py` | AC-P4-5 |
| `tests/integration/test_checkpoint_resume.py` | AC-P4-6 |
| Unit/integration: command approve/reject gate | AC-P4-4, AC-P4-7 |
| Unit/integration: phase markdown present | AC-P4-8 |

Prefer fixture/temp targets + mock provider.

## Suggested build order

```text
WP1 CommandRunner (propose → approve/reject → run; no GitSafety)
  → WP2 state + schedule/execute/sync with mock “agent” no-ops
  → WP6 seq/logical-parallel tests green
  → WP3 Developer + Testing (Workspace writes + command gate)
  → WP4 retry + safe-stop + destructive interrupt + WP6 tests
  → checkpointer + resume + WP6 resume tests
  → WP0/WP5 CLI polish (--interactive command prompts)
  → docs stub + phase markdown
```

If time-short: **protect** seq/logical-parallel + command approve gate + retry cap + resume. Git flow stays off.

## Demo script (lead review)

```text
python -m pip install -e ".[dev]"
pytest tests/integration/test_workflow_seq_parallel.py \
       tests/integration/test_retry_and_safe_stop.py \
       tests/integration/test_checkpoint_resume.py

agentic init ../phase4-fixture
# drive through Phase 2–3 to plan approval (mock), then:
agentic run ../phase4-fixture --interactive
# at command gate: approve pytest (or reject a dangerous proposal)
agentic status ../phase4-fixture
# force failure path in fixture → retry then safe-stop OR success
# kill mid-run → agentic resume ../phase4-fixture
```

## Exit criteria

- [x] AC-P4-1 … AC-P4-9 in [SPEC.md](SPEC.md) satisfied or explicitly waived by lead
- [x] Integration tests above green under mock provider
- [x] No new LLM client; Anthropic/mock still via Phase 2 factory
- [x] Limitations documented (replan stub, docs stub, no release gate, no git flow)
- [ ] Lead approval before Phase 5

## Explicit non-goals this phase

- **Git flow / GitSafety** (disabled until lead re-enables)
- True concurrent Send/map-reduce parallelism
- Silent command execution without approve
- Metrics dashboard / MTTR report (`agentic report`)
- Dynamic replan + re-approve
- Release gate
- Real product demo apps (Phase 6)

## Risk notes

| Risk | Mitigation |
| --- | --- |
| Approval fatigue (every command) | Clear proposal text; interactive + explicit approve UX; batch later if lead allows |
| Checkpointer vs JSON confusion | Resume only via LangGraph thread id; document dual persistence |
| Agent overreach | Workspace for files; no silent shell; Python owns transitions |
| Scope creep into Phase 5 | Stub replan/docs/report; stop at execution demo |
