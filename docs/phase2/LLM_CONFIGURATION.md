# Phase 2 LLM configuration

LLM provider support is delivered in **Phase 2**. Later phases must **reuse** this abstraction — do not add a second provider stack in Phases 3–6.

## Supported providers

| `AGENTIC_LLM_PROVIDER` | Behavior |
| --- | --- |
| `mock` (default) | Deterministic / queued responses; CI-safe; no network |
| `anthropic` | Claude via Anthropic Messages API |

## Install for live Anthropic runs

```text
python -m pip install -e ".[dev,anthropic]"
```

## Configure Anthropic

PowerShell (session):

```powershell
$env:AGENTIC_LLM_PROVIDER = "anthropic"
$env:AGENTIC_LLM_MODEL = "claude-sonnet-4-5"
$env:AGENTIC_LLM_API_KEY = "sk-ant-..."   # or: $env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Or copy `.env.example` → `.env` (gitignored):

```text
AGENTIC_LLM_PROVIDER=anthropic
AGENTIC_LLM_MODEL=claude-sonnet-4-5
AGENTIC_LLM_API_KEY=sk-ant-...
```

Then run the usual Phase 2 CLI flow. Analyzer and spec generator will call Claude and expect JSON.

## Defaults

- If provider is `anthropic` and model is unset/`mock-model`, model becomes `claude-sonnet-4-5`.
- API key resolution order: `AGENTIC_LLM_API_KEY` → `ANTHROPIC_API_KEY`.

## Tests

CI stays on `mock`. Anthropic unit tests mock the SDK client and never call the network.

## Out of scope (do not re-implement later)

- Multi-provider routing / fallback chains
- Prompt caching / vector retrieval
- OpenAI adapter (optional future add behind the same `LLMProvider` protocol — not a new subsystem)
