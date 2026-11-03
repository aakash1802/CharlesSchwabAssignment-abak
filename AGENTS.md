# Agent guide

Working agreement for coding agents in this repository. Read this file before changing the project.

## Current phase

**Active build scope: Phases 0–6.**

Lead intent: implement **Phase 6** (demo / packaging) per [docs/phase6/](docs/phase6/). Demo target is the sibling project `../abassign1` (outside this tree).

| Phase | State |
| --- | --- |
| 0 Architecture | Approved |
| 1 Foundation | Approved |
| 2 Requirement intelligence | Approved |
| 3 Planning and dependency graph | Approved |
| 4 Agentic execution | Implemented (vertical slice) — LLM codegen/test/docs when provider live; mock stubs offline |
| 5 Governance and reliability | Implemented (vertical slice) — [docs/phase5/](docs/phase5/) |
| 6 Demo / packaging | Delivered (seed + DEMO.md) — [docs/phase6/](docs/phase6/); target `../abassign1`; operator live runs remaining |

- Requirements: [REQUIREMENTS.md](REQUIREMENTS.md)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md) (full plan remains valid; later phases unchanged)
- Decisions: [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md)
- Plan: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

This repository is the **Agentic Engineer CLI only**. Target applications are sibling directories outside this tree. Never place target application source inside this repo; never place CLI implementation inside a target. Phase 6 complete project: `../abassign1` (FastAPI ShareApp).

## Read first

1. [README.md](README.md) for status and layout.
2. [REQUIREMENTS.md](REQUIREMENTS.md) for scope and acceptance criteria.
3. [ARCHITECTURE.md](ARCHITECTURE.md) and [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) for design.
4. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for phases.
5. Phase 6 runbook: [docs/phase6/DEMO.md](docs/phase6/DEMO.md).

## How to work

- Prefer operator verification via [TEST_CHECKLIST.md](TEST_CHECKLIST.md) / [docs/phase6/DEMO.md](docs/phase6/DEMO.md) over new features unless the lead reopens scope.
- Phase 4 command policy: propose any argv/shell, **always** human approve/reject before run (no silent execution).
- Update the matching document when behavior, scope, or structure changes.
- Do not commit secrets, tokens, or local environment files.
- Do not treat `.venv` as source. Do not edit files inside it.
- Do not copy `abassign1` application source into this repository.

## LLM providers (Phase 2 — do not rebuild later)

- `mock` (default) and `anthropic` via `build_provider()`
- Config: [docs/phase2/LLM_CONFIGURATION.md](docs/phase2/LLM_CONFIGURATION.md), [`.env.example`](.env.example)
- Phases 3+ must inject/`build_provider()` — no second LLM subsystem
- Execution agents (Developer / Testing / Documentation) use the same provider: live Anthropic produces real target files and command proposals; default mock keeps deterministic stubs for offline pytest.

## Verification (Phase 4–6)

```text
python -m pip install -e ".[dev]"
pytest
agentic init ../abassign1

# Interactive through plan + command gates
agentic run ../abassign1 --interactive --requirement "Improve sharing security"

# Explicit gates
agentic run ../abassign1 --requirement "Improve sharing security"
agentic status ../abassign1
agentic run ../abassign1 --answer "..." --answer "..."
agentic approve ../abassign1
# → auto-generates plan; parks at awaiting_plan_approval
agentic approve ../abassign1
# → plan approved; execution auto-starts; parks at awaiting_command_approval when needed
agentic approve ../abassign1
# → approve command / release gates until completed
agentic status ../abassign1
agentic report ../abassign1
```

Full Phase 6 scenarios (greenfield / brownfield / ambiguous): [docs/phase6/DEMO.md](docs/phase6/DEMO.md).
