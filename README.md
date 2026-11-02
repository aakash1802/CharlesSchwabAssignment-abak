# Agentic Engineer (Charles Schwab Assignment)

Prototype of a **standalone agentic software-engineering CLI**: it creates, modifies, tests, and documents *other* projects under controlled autonomy.

Concrete demonstration target applications are **deferred** and will be defined later. This repository is the CLI only.

## Status

| Item | State |
| --- | --- |
| Requirements | [REQUIREMENTS.md](REQUIREMENTS.md) |
| Architecture | Phase 0 approved (full plan retained) |
| Phase 1 foundation | Approved |
| Phase 2 requirement intelligence | **Current boundary** — implemented; audit package ready |
| Phase 2 audit / review artifacts | [docs/phase2/](docs/phase2/) |
| Phases 3–6 | Deferred until lead explicitly resumes |
| Demo target apps | Deferred |
| Runtime | Python 3.11+; install with `pip install -e ".[dev]"` |

Lead intent: build and test **through Phase 2 for now**; resume later phases afterward without changing the architecture.

### Phase 2 review package

See [docs/phase2/README.md](docs/phase2/README.md) for the delivery report, acceptance checklist, reviewer guide, pytest capture, and sample `.agentic` artifacts.

### LLM configuration (Phase 2)

Default is `mock` (no API key). For Anthropic:

```powershell
python -m pip install -e ".[dev,anthropic]"
$env:AGENTIC_LLM_PROVIDER = "anthropic"
$env:AGENTIC_LLM_MODEL = "claude-sonnet-4-5"
$env:AGENTIC_LLM_API_KEY = "sk-ant-..."   # or ANTHROPIC_API_KEY
```

Details: [docs/phase2/LLM_CONFIGURATION.md](docs/phase2/LLM_CONFIGURATION.md) and [`.env.example`](.env.example).

## Product boundary

```text
PycharmProjects/
├── CharlesSchwabAssignment-abak/   ← this repo = Agentic Engineer CLI
└── <target-project>/               ← separate target (later)
    └── .agentic/                   ← workflow metadata only
```

## Quick start (Phase 1)

```text
python -m pip install -e ".[dev]"
pytest
agentic version
agentic init ../target-a
agentic init ../target-b
agentic status ../target-a
# agentic init .   → must fail (cannot target CLI repo)
```

## Documentation

| Document | Purpose |
| --- | --- |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Scope and acceptance criteria |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |
| [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) | ADRs and trade-offs |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Phased delivery |
| [AGENTS.md](AGENTS.md) | Working agreement for coding agents |

## Repository layout

```text
.
├── pyproject.toml
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
