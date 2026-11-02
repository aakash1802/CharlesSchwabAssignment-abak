# Agent guide

Working agreement for coding agents in this repository. Read this file before changing the project.

## Current phase

**Active build scope: Phases 0–3.**

Lead intent: implement, test, and stabilize through **Phase 3** (planning and dependency graph). **Do not start Phase 4+** until the lead explicitly resumes later phases.

| Phase | State |
| --- | --- |
| 0 Architecture | Approved |
| 1 Foundation | Approved |
| 2 Requirement intelligence | Approved |
| 3 Planning and dependency graph | Implemented — test/stabilize; notes in `docs/phase3/` |
| 4–6 | Deferred until lead resumes |

- Requirements: [REQUIREMENTS.md](REQUIREMENTS.md)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md) (full plan remains valid; later phases unchanged)
- Decisions: [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md)
- Plan: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

This repository is the **Agentic Engineer CLI only**. Target applications are sibling directories outside this tree. Never place target application source inside this repo; never place CLI implementation inside a target. Concrete demo target apps remain deferred (Phase 6).

## Read first

1. [README.md](README.md) for status and layout.
2. [REQUIREMENTS.md](REQUIREMENTS.md) for scope and acceptance criteria.
3. [ARCHITECTURE.md](ARCHITECTURE.md) and [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) for design.
4. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for phases and the pause-at-Phase-3 rule.

## How to work

- Keep changes inside the Phase 0–3 surface unless the lead reopens Phase 4+.
- Prefer completing/testing Phase 3 over adding Phase 4 features.
- Update the matching document when behavior, scope, or structure changes.
- Do not commit secrets, tokens, or local environment files.
- Do not treat `.venv` as source. Do not edit files inside it.

## LLM providers (Phase 2 — do not rebuild later)

- `mock` (default) and `anthropic` via `build_provider()`
- Config: [docs/phase2/LLM_CONFIGURATION.md](docs/phase2/LLM_CONFIGURATION.md), [`.env.example`](.env.example)
- Phases 3+ must inject/`build_provider()` — no second LLM subsystem

## Verification (Phase 3)

```text
python -m pip install -e ".[dev]"
pytest
agentic init ../target-a
agentic run ../target-a --requirement "Improve sharing security"
agentic status ../target-a
agentic run ../target-a --answer "..." --answer "..."
agentic approve ../target-a
# → auto-generates plan; parks at awaiting_plan_approval
agentic plan ../target-a
agentic approve ../target-a
agentic plan ../target-a
agentic status ../target-a
```
