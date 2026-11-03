# Agentic Engineer (Charles Schwab Assignment)

Prototype of a **standalone agentic software-engineering CLI**: it creates, modifies, tests, and documents *other* projects under controlled autonomy.

This repository is the **CLI only**. Phase 6 complete demo target lives at sibling `../abassign1` (FastAPI ShareApp) — never embed target source here.

## Status

| Item | State |
| --- | --- |
| Requirements | [REQUIREMENTS.md](REQUIREMENTS.md) |
| Architecture | Phase 0 approved (full plan retained) |
| Phase 1 foundation | Approved |
| Phase 2 requirement intelligence | Approved |
| Phase 2 audit / review artifacts | [docs/phase2/](docs/phase2/) |
| Phase 3 planning / dependency graph | Approved — see [docs/phase3/](docs/phase3/) |
| Phase 4 agentic execution | Implemented (vertical slice) — see [docs/phase4/](docs/phase4/) |
| Manual test checklist | [TEST_CHECKLIST.md](TEST_CHECKLIST.md) |
| Phase 5 governance | Implemented (vertical slice) — [docs/phase5/](docs/phase5/) |
| Phase 6 demo / packaging | Delivered (runbook + seed) — [docs/phase6/](docs/phase6/); target `../abassign1`; live runs via [TEST_CHECKLIST.md](TEST_CHECKLIST.md) / [DEMO.md](docs/phase6/DEMO.md) |
| Demo target app | Sibling `../abassign1` (complete project packaging) |
| Runtime | Python 3.11+; install with `pip install -e ".[dev]"` |

Lead intent: Phase 6 demo/runbook against `../abassign1`. Reviewer steps: [docs/phase6/DEMO.md](docs/phase6/DEMO.md).

### Phase 2 review package

See [docs/phase2/README.md](docs/phase2/README.md) for the delivery report, acceptance checklist, reviewer guide, pytest capture, and sample `.agentic` artifacts.

### LLM configuration (Phase 2)

Default is `mock`. For Anthropic via config file (recommended):

```powershell
python -m pip install -e ".[dev,anthropic]"
copy agentic.config.example.toml agentic.toml
# edit agentic.toml → set [llm] api_key / provider / model
python agenticli_test.py --config .\agentic.toml run ..\phase2-test-target --requirement "..."
```

Also supports `~/.agentic/config.toml`, `AGENTIC_*` env vars, and `.env`.  
Details: [docs/phase2/LLM_CONFIGURATION.md](docs/phase2/LLM_CONFIGURATION.md).

## Product boundary

```text
PycharmProjects/
├── CharlesSchwabAssignment-abak/   ← this repo = Agentic Engineer CLI
└── abassign1/                      ← Phase 6 complete demo target (FastAPI)
    ├── src/shareapp/
    └── .agentic/                   ← workflow metadata only (after CLI runs)
```

## Quick start

```powershell
python -m pip install -e ".[dev]"
pytest
```

### Local test launcher (recommended)

From the repo root:

```powershell
python agenticli_test.py --help
python agenticli_test.py version

# Init target (outside this repo)
python agenticli_test.py init ..\phase2-test-target

# Interactive end-to-end (prompts for clarification + approvals in one session)
python agenticli_test.py run ..\phase2-test-target --interactive --requirement "Improve sharing security"

# Or non-interactive / explicit gates (also supported)
python agenticli_test.py run ..\phase2-test-target --requirement "Improve sharing security"
python agenticli_test.py run ..\phase2-test-target --requirement-file .\requirement.md
python agenticli_test.py status ..\phase2-test-target
python agenticli_test.py spec ..\phase2-test-target
python agenticli_test.py run ..\phase2-test-target --answer "..." --answer "..."
python agenticli_test.py approve ..\phase2-test-target --comment "ok"
python agenticli_test.py reject ..\phase2-test-target --comment "rework"
python agenticli_test.py plan ..\phase2-test-target
python agenticli_test.py approve ..\phase2-test-target --comment "plan ok"

# Phase 4 — execute (approve-before-run for commands)
python agenticli_test.py run ..\phase2-test-target --interactive
# or non-interactive: resume + approve command gates
python agenticli_test.py resume ..\phase2-test-target
python agenticli_test.py approve ..\phase2-test-target --comment "run tests"
python agenticli_test.py status ..\phase2-test-target
python agenticli_test.py spec ..\phase2-test-target
```

Also available: `agentic` console script, or `python -m agentic_engineer`.

**Full step-by-step test script:** [TEST_CHECKLIST.md](TEST_CHECKLIST.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Scope and acceptance criteria |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |
| [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) | ADRs and trade-offs |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Phased delivery |
| [AGENTS.md](AGENTS.md) | Working agreement for coding agents |
| [TEST_CHECKLIST.md](TEST_CHECKLIST.md) | Manual test commands (init, requirement file, status, spec, …) |
| [docs/phase2/](docs/phase2/) | Phase 2 audit / review package |
| [docs/phase3/](docs/phase3/) | Phase 3 planning / dependency graph notes |
| [docs/phase4/](docs/phase4/) | Phase 4 agentic execution spec / plan |

## Repository layout

```text
.
├── pyproject.toml
├── agenticli_test.py
├── TEST_CHECKLIST.md
├── src/agentic_engineer/
│   ├── cli/
│   ├── config/
│   ├── models/
│   ├── workspace/
│   ├── persistence/
│   ├── llm/
│   ├── graph/          # requirement + execution LangGraph
│   ├── agents/
│   ├── governance/
│   └── execution/      # CommandRunner (git safety deferred)
└── tests/{unit,integration}/
```

## License

Not set.
