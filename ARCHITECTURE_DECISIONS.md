# Architecture Decisions

Record of decisions for the Agentic Engineer prototype. Each entry states the decision, context, alternatives, consequences, and prototype implications.

**Status:** Phase 0 approved by technical lead.

**Companion docs:** [ARCHITECTURE.md](ARCHITECTURE.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

---

## ADR-001 — This repository is the CLI only

**Decision:** `CharlesSchwabAssignment-abak` is Project A (Agentic Engineer CLI). Target applications are separate directories **outside** this repository. Concrete demo apps are deferred and will be chosen later.

**Context:** The assignment product is a reusable development tool. Placing any target app inside the CLI tree blurs ownership and invites circular dependencies.

**Alternatives:** Monorepo with `packages/cli` + `packages/<app>`; nested `demos/` inside CLI.

**Consequences:** CLI CI and packaging stay focused on the tool. Integration against real apps happens later via external paths / temp workspaces.

**Challenge rejected:** Shipping a demo application under `src/` in this repo for convenience.

---

## ADR-002 — Sibling targets, not a mandatory `workspace/` parent

**Decision:** Isolation is enforced by the Workspace abstraction and path rules. A cosmetic parent folder named `workspace/` is optional and **not** required for correctness.

**Context:** The brief shows `workspace/agentic-engineer` + siblings. This repo already exists at `PycharmProjects/CharlesSchwabAssignment-abak`.

**Alternatives:** Rename/move into `workspace/agentic-engineer` immediately.

**Consequences:** Less churn now; docs describe logical layout. Rename can happen later without changing architecture.

---

## ADR-003 — Language and core stack

**Decision:** Python 3.11+, Typer, Pydantic v2, LangGraph, Pytest, JSON files + LangGraph-compatible checkpointer, structured logging, env-based secrets.

**Context:** Matches the proposed stack and the existing local `.venv`. Fits a 5–6 hour prototype.

**Alternatives:** Node/TypeScript agent framework; CrewAI/AutoGen; custom asyncio state machine without LangGraph.

**Consequences:** One ecosystem; LangGraph interrupts/checkpoints map cleanly to approval and resume. We accept Python packaging overhead (`pyproject.toml`, console script).

**Rejected:** Second orchestration framework alongside LangGraph; Postgres/Redis/vector DB for the prototype.

---

## ADR-004 — LLM intelligence, deterministic control

**Decision:** LLMs produce structured artifacts and recommendations. Python owns transitions, dependency enforcement, approvals, retry caps, path policy, command policy, and safe-stop.

**Context:** Assignment requires controlled autonomy and forbids LLM self-approval.

**Consequences:** Agent modules stay thin; governance tests do not need an LLM. Structured output + Pydantic validation at the intelligence boundary.

---

## ADR-005 — Provider abstraction with mock + Anthropic (Phase 2)

**Decision:** Define a small `LLMProvider` protocol (complete + timeout/error mapping). Ship `MockProvider` for unit/integration tests and **`AnthropicProvider`** for live runs. Delivered in **Phase 2** — later phases reuse `build_provider()` / `LLMProvider`; do not introduce a parallel LLM stack.

**Context:** CI must not require paid calls; swapping models must not rewrite agents. Lead requested Anthropic configuration for CLI testing.

**Consequences:** Prompts live beside agents; providers return text (JSON extracted when structured). Credentials via `AGENTIC_LLM_API_KEY` or `ANTHROPIC_API_KEY` — never committed. Optional install: `pip install -e ".[anthropic]"`. OpenAI (or others) may be added later as another `LLMProvider` implementation only.

---

## ADR-006 — Eight agent *roles*, progressive depth

**Decision:** Keep the eight named responsibilities from the brief as separate modules/interfaces, but implement depth by phase. Architecture and Documentation may stay intentionally thin in the first vertical slice.

**Context:** “An agent per tiny operation” is rejected; eight is already the upper bound for this prototype. Implementing all eight at full sophistication in one pass will blow the time box.

**Alternatives:** Merge Architecture into Task Planner; merge Documentation into Reporting.

**Consequences:** Clear narrative (“specialized agents”) without empty placeholder packages. If time is critical in Phase 4, Architecture can be “deterministic inspect + one LLM design summary.”

**Challenge:** Creating eight empty files in Phase 1 “for completeness” is rejected (engineering constraint 13).

---

## ADR-007 — LangGraph as the only orchestrator; task graph as data

**Decision:** Use one LangGraph `StateGraph` for workflow control. Represent engineering tasks and dependencies as validated JSON/Pydantic data. Do not build a custom DAG executor.

**Context:** Brief forbids a parallel custom DAG engine. Dependency-aware execution still needs an inspectable graph.

**Consequences:** Scheduling logic: compute ready set from task graph → LangGraph node(s) execute ready tasks (fan-out) → write statuses back → loop until done or stop. Graph validation is pure Python unit-tested without LangGraph.

---

## ADR-008 — Dual persistence

**Decision:** (1) Human-readable project artifacts under `<target>/.agentic/` (specs, plans, approvals, audit). (2) LangGraph checkpointer for resume/interrupts. Treat them as separate concerns; do not assume `state.json` alone resumes the graph.

**Context:** Brief explicitly separates application JSON persistence from LangGraph checkpointing.

**Consequences:** Thread/workflow ids stored in `.agentic` config; resume loads checkpointer first. Slightly more code; correct recovery story for the assignment.

---

## ADR-009 — Approval via interrupt + CLI commands

**Decision:** Pending approvals park the graph (`interrupt`). Humans decide with `agentic approve` / `reject` (and optional comment). Orchestration validates the record before resuming.

**Context:** LLM-generated approval booleans are forbidden.

**Alternatives:** Always stdin prompts inside `run` (simpler but weaker for resume-after-exit demos).

**Consequences:** Slightly more CLI surface; stronger “controlled autonomy” story and crash-safe waiting.

---

## ADR-010 — Retry cap default = 2; Failure Analysis cannot raise it

**Decision:** Configurable `max_task_retries` defaulting to 2. Failure Analysis may recommend retry vs replan vs stop; the orchestrator enforces the cap and safe-stop.

**Context:** Unbounded agent loops are a common failure mode.

**Consequences:** Simple, demonstrable governance. Exhausted retries → safe-stop with preserved state.

---

## ADR-011 — Simplified dynamic replanning

**Decision:** For the prototype, replan = structured **plan patch** (add/replace tasks, invalidate impacted downstream, preserve completed unaffected work) + dependency revalidation + human approval when scope/risk expands. No autonomous full-plan regeneration loop.

**Context:** Full continuous replanning is a research project; the brief asks to record why the plan changed and avoid blind full regenerations.

**Consequences:** Honest limitation in the write-up; still demonstrates controlled adaptation.

---

## ADR-012 — Metrics from audit events

**Decision:** Append audit events as the source of truth. Derive metrics in `report` / `metrics.json`. Never invent values; say “insufficient data” when needed.

**Context:** Separate metrics pipelines are unnecessary for a file-based prototype.

**Consequences:** One write path; metrics quality depends on instrumentation discipline in Phases 4–5.

---

## ADR-013 — Command execution (approve-before-run)

**Decision (Phase 4 amendment):** Agents may **propose** any argv/shell string. `CommandRunner` must **never** execute silently: every proposed command interrupts for human `approve` / `reject` first. On approve, run with fixed cwd=workspace root (or approved subdir), timeout, and captured stdout/stderr/exit. The LLM must not write the approval decision.

**Prior decision:** Hard allowlist-only execution (deny unknown commands without a human gate).

**Context:** Lead chose a relaxed propose-any-command model with mandatory human gate (2026-11-03) so demos stay flexible without silent shell. Unrestricted *silent* shell remains incompatible with the brief (R8).

**Consequences:** More approval interrupts during Testing/execution; dual UX (`--interactive` prompts + explicit `approve`/`reject`) required. Optional allowlist for auto-approve of known-safe commands may be added later only with explicit lead approval.

---

## ADR-014 — Git safety without hard reset

**Decision:** Before modifying an existing repo: inspect status; if unexpected dirty user changes conflict with the workflow, **stop**. Prefer creating an `agentic/<workflow-id>` branch and commits as checkpoints. Never `git reset --hard` to discard pre-existing user work.

**Context:** Brief forbids blind hard reset; rollback must not destroy user changes.

**Consequences:** Rollback may be “stop and instruct human” when unsafe — acceptable prototype behavior.

---

## ADR-015 — Target app design deferred

**Decision:** No concrete target application, API surface, or app stack is decided in Phase 0. The CLI must remain target-agnostic. Demo apps and scenarios will be specified in a later phase.

**Context:** Lead requested demo-app concerns be removed from the current architecture context.

**Consequences:** Architecture approval does not include FastAPI/Flask/shortener (or any other) choices. Phase 6 (or a dedicated demo phase) will define targets later.

---

## ADR-016 — Brownfield means inspect-first, minimal diff

**Decision:** Non-empty targets trigger repository inspection and impact analysis before plan approval. The system must not replace project structure to match a preferred template without justification and approval.

**Context:** Reusability across existing codebases.

**Consequences:** Architecture agent / inspect node is mandatory before planning on existing trees (Phase 4).

---

## Challenges to the brief (recommendations)

| Brief idea | Challenge | Recommendation |
| --- | --- | --- |
| Full parallel sophistication everywhere | Expensive to get right with interrupts | One fan-out/fan-in pattern for independent ready tasks |
| Rich MTTR and full metric suite | Easy to fake or under-instrument | Metrics-from-events; list N/A when thin |
| Exact `workspace/` tree | Repo already named/located | Logical separation now; rename optional later |
| All eight agents deep by day one | Time box | Progressive depth (ADR-006) |
| Dynamic replanning engine | Scope risk | Plan patches + approval (ADR-011) |
| Demo app in architecture now | Lead deferred | ADR-015 — define later |

---

## Decision log (checkbox for lead)

- [x] ADR-001 CLI-only repo
- [x] ADR-002 Optional `workspace/` parent
- [x] ADR-003 Stack
- [x] ADR-004 Deterministic control
- [x] ADR-005 Provider + mock
- [x] ADR-006 Agent roles progressive
- [x] ADR-007 LangGraph + graph-as-data
- [x] ADR-008 Dual persistence
- [x] ADR-009 Interrupt approvals
- [x] ADR-010 Retry cap = 2
- [x] ADR-011 Simplified replan
- [x] ADR-012 Metrics from audit
- [x] ADR-013 Command allowlist
- [x] ADR-014 Git no hard reset
- [x] ADR-015 Target app design deferred
- [x] ADR-016 Brownfield inspect-first
