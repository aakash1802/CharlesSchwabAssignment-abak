# Agentic Engineer (Charles Schwab Assignment)

Prototype of a **standalone agentic software-engineering CLI**: it creates, modifies, tests, and documents *other* projects under controlled autonomy.

Concrete demonstration target applications are **deferred** and will be defined later. This repository is the CLI only.

## Status

| Item | State |
| --- | --- |
| Requirements | [REQUIREMENTS.md](REQUIREMENTS.md) |
| Architecture | Phase 0 approved (full plan retained) |
| Phase 1 foundation | Approved |
| Phase 2 requirement intelligence | Approved |
| Phase 2 audit / review artifacts | [docs/phase2/](docs/phase2/) |
| Phase 3 planning / dependency graph | **Current boundary** — implemented; see [docs/phase3/](docs/phase3/) |
| Manual test checklist | [TEST_CHECKLIST.md](TEST_CHECKLIST.md) |
| Phases 4–6 | Deferred until lead explicitly resumes |
| Demo target apps | Deferred |
| Runtime | Python 3.11+; install with `pip install -e ".[dev]"` |

Lead intent: build and test **through Phase 3**; resume Phase 4+ only after explicit lead approval.

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
└── <target-project>/               ← separate target (later)
    └── .agentic/                   ← workflow metadata only
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

# Start workflow (inline or file)
python agenticli_test.py run ..\phase2-test-target --requirement "Improve sharing security"
python agenticli_test.py run ..\phase2-test-target --requirement-file .\requirement.md

# Inspect
python agenticli_test.py status ..\phase2-test-target
python agenticli_test.py spec ..\phase2-test-target

# Clarification answers (when status is awaiting_clarification)
python agenticli_test.py run ..\phase2-test-target --answer "..." --answer "..."

# Human decision (specification gate)
python agenticli_test.py approve ..\phase2-test-target --comment "ok"
python agenticli_test.py reject ..\phase2-test-target --comment "rework"

# Spec approve auto-generates the plan; inspect / approve plan gate
python agenticli_test.py plan ..\phase2-test-target
python agenticli_test.py approve ..\phase2-test-target --comment "plan ok"
python agenticli_test.py plan ..\phase2-test-target

# Status / spec after decision
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
│   └── llm/
└── tests/unit/
```

## License

Not set.
