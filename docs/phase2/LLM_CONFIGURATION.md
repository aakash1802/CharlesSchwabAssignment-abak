# Phase 2 LLM configuration

LLM provider support is delivered in **Phase 2**. Later phases must **reuse** this abstraction — do not add a second provider stack in Phases 3–6.

## Supported providers

| Provider | Behavior |
| --- | --- |
| `mock` (default) | Deterministic / queued responses; CI-safe; no network |
| `anthropic` | Claude via Anthropic Messages API |

## Structured outputs (Developer Agent)

The Developer Agent sends a JSON Schema (`DeveloperFiles`) on the request. Anthropic prefers provider-constrained JSON via `output_config.format` (falls back to tool-use input schema, then prompted JSON). Responses are validated with Pydantic before any workspace write. Oversized tasks are generated in bounded file batches (`developer_max_files_per_batch`, default 5). Truncation (`stop_reason=max_tokens`) is classified and retried with reduced scope — not as a generic transient failure.

## Install for live Anthropic runs

```text
python -m pip install -e ".[dev,anthropic]"
```

## Configure via TOML file (recommended for local testing)

Copy the example and edit (do not commit secrets):

```text
copy agentic.config.example.toml agentic.toml
```

Example `agentic.toml` (repo root or cwd):

```toml
log_level = "INFO"

[llm]
provider = "anthropic"
model = "claude-sonnet-5-5"
api_key = "sk-ant-your-key-here"
timeout_seconds = 60
max_tokens = 4096
```

Or user-global:

```text
%USERPROFILE%\.agentic\config.toml
```

### Discovery order

1. `python agenticli_test.py --config path\to\file.toml ...`
2. `AGENTIC_CONFIG` env var (path to a TOML file)
3. `./agentic.toml` or `./agentic.config.toml` (current working directory)
4. `~/.agentic/config.toml`

### Precedence (highest wins)

CLI/`AGENTIC_*` environment variables → `.env` → TOML config file → defaults.

So a key in `agentic.toml` is used unless overridden by env.

### Run with config

```powershell
python agenticli_test.py --config .\agentic.toml run ..\phase2-test-target --requirement "Improve sharing security"

# or rely on ./agentic.toml discovery
python agenticli_test.py run ..\phase2-test-target --requirement "Improve sharing security"
```

## Configure via environment (optional)

```powershell
$env:AGENTIC_LLM_PROVIDER = "anthropic"
$env:AGENTIC_LLM_MODEL = "claude-sonnet-5-5"
$env:AGENTIC_LLM_API_KEY = "sk-ant-..."   # or ANTHROPIC_API_KEY
```

## Invoking the CLI

```powershell
python agenticli_test.py --help
python agenticli_test.py init ..\target-a
python agenticli_test.py run ..\target-a --requirement "..."
```

## Defaults

- If provider is `anthropic` and model is unset/`mock-model`, model becomes `claude-sonnet-5-5`.
- API key resolution: settings/`AGENTIC_LLM_API_KEY` → `ANTHROPIC_API_KEY`.

## Tests

CI stays on `mock`. Config-file and Anthropic unit tests do not call the live API.

## Out of scope (do not re-implement later)

- Multi-provider routing / failover chains
- Prompt caching / vector retrieval
- OpenAI adapter (optional future `LLMProvider` only — not a new subsystem)
