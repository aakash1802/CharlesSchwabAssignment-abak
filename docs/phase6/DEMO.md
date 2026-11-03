# Phase 6 demo runbook — `../abassign1`

Reproduce greenfield, brownfield, and ambiguous workflows against the sibling FastAPI target. Run all CLI commands from the **CLI repo root** (`CharlesSchwabAssignment-abak`) unless noted.

| Item | Value |
| --- | --- |
| Target path | `..\abassign1` → `C:\Users\Avita\PycharmProjects\abassign1` |
| Stack | FastAPI share-link mini-app (`shareapp`) |
| CLI launcher | `python agenticli_test.py` (or `agentic` after install) |
| Packaging | Complete project lives at `..\abassign1`; CLI stays in this repo |

Default LLM is `mock`. For a live demo, configure Anthropic per [docs/phase2/LLM_CONFIGURATION.md](../phase2/LLM_CONFIGURATION.md).

---

## 0. Prerequisites

```powershell
# CLI repo
cd C:\Users\Avita\PycharmProjects\CharlesSchwabAssignment-abak
python -m pip install -e ".[dev]"
pytest -q
```

Confirm the seed project exists and is independent of the CLI (section 4).

Expected gates during a full run (Phases 2–5): clarification (if ambiguous) → spec approval → plan approval → command approval(s) → release approval (success path) → `agentic report`.

---

## 1. Greenfield — empty directory → scaffold

Use a **throwaway** empty sibling so the durable seed at `abassign1` is not wiped. Path: `..\abassign1-greenfield`.

```powershell
# From CLI repo root
$gf = "..\abassign1-greenfield"
if (Test-Path $gf) { Remove-Item -Recurse -Force $gf }
New-Item -ItemType Directory -Path $gf | Out-Null

python agenticli_test.py init $gf
python agenticli_test.py run $gf --interactive --requirement "Create a minimal FastAPI app named ShareApp with GET /health returning status ok, POST /shares that stores a note and returns a token, and GET /shares/{token} that returns the note. Include a README and a pytest smoke test. Do not depend on agentic-engineer."
```

At interactive prompts: answer any clarifications; approve spec (`a`) and plan (`a`); approve proposed commands; approve release when parked at `awaiting_release_approval`.

```powershell
python agenticli_test.py status $gf
python agenticli_test.py report $gf
```

Inspect:

- `$gf\.agentic\readable\` (SPEC / PLAN / REPORT / phase summaries)
- `$gf\.agentic\reports\`
- `$gf\.agentic\workflows\workflow_*\execution_history.json`

**Terminal / gated states:** progress through approvals to successful complete after release, or a documented park (`awaiting_*`, `safe_stopped`). Target must still have no CLI runtime dependency.

---

## 2. Brownfield — improve sharing security on the seed

Use the complete seed at `..\abassign1` (see that project’s `SEED.md` / `README.md`).

```powershell
# Optional: clear prior workflow state for a clean run
Remove-Item -Recurse -Force ..\abassign1\.agentic -ErrorAction SilentlyContinue

python agenticli_test.py init ..\abassign1
python agenticli_test.py run ..\abassign1 --interactive --requirement "Improve sharing security: private shares must not appear in GET /shares for anonymous callers; GET /shares/{token} for non-public shares must require an owner query parameter matching the share owner; keep public shares readable without auth."
```

Approve gates as above. Then:

```powershell
python agenticli_test.py status ..\abassign1
python agenticli_test.py report ..\abassign1
python agenticli_test.py history ..\abassign1
```

Inspect `..\abassign1\.agentic\` as in greenfield. Re-run target tests from the target venv (section 4) to confirm the app still runs without the CLI.

**Explicit-gate alternative** (non-interactive):

```powershell
python agenticli_test.py run ..\abassign1 --requirement "Improve sharing security: private shares must not appear in GET /shares for anonymous callers; GET /shares/{token} for non-public shares must require an owner query parameter matching the share owner; keep public shares readable without auth."
python agenticli_test.py status ..\abassign1
# answer clarifications if needed:
# python agenticli_test.py run ..\abassign1 --answer "..." --answer "..."
python agenticli_test.py approve ..\abassign1
# → plan generated; awaiting_plan_approval
python agenticli_test.py approve ..\abassign1
# → plan approved; execution auto-starts; usually awaiting_command_approval
# when awaiting_command_approval / awaiting_release_approval:
python agenticli_test.py approve ..\abassign1
# if you exited mid-flight without a pending gate: agenticli_test.py resume ..\abassign1
```

---

## 3. Ambiguous — clarification gates

Against the same seed (reset `.agentic` if you want a fresh workflow):

```powershell
Remove-Item -Recurse -Force ..\abassign1\.agentic -ErrorAction SilentlyContinue
python agenticli_test.py init ..\abassign1
python agenticli_test.py run ..\abassign1 --interactive --requirement "Make sharing better and safer somehow"
```

Example clarification answers (adapt to prompts):

```text
Require signed or owner-scoped access for private shares
Do not remove public share reads
Expire private share tokens after 24 hours if you add expiry
```

Then approve spec / plan / commands / release as parked. Expect early status `awaiting_clarification` before answers; afterward the same approval chain as brownfield.

```powershell
python agenticli_test.py status ..\abassign1
python agenticli_test.py report ..\abassign1
```

---

## 4. Independence check (AC-P6-1 / R9)

From **`abassign1`** (or greenfield path), without relying on the CLI package:

```powershell
cd C:\Users\Avita\PycharmProjects\abassign1
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn shareapp.main:app --port 8001
# Ctrl+C when done
```

Dependency check (must find **no** matches):

```powershell
Select-String -Path .\pyproject.toml,.\requirements.txt -Pattern "agentic-engineer|agentic_engineer"
```

Expect: no output (no CLI dependency).

CLI packaging check (from CLI repo): target application source must **not** live under the CLI tree:

```powershell
cd C:\Users\Avita\PycharmProjects\CharlesSchwabAssignment-abak
Test-Path .\abassign1
# Expect: False
```

---

## 5. What “done” looks like

| Mode | Success signal |
| --- | --- |
| Greenfield | Scaffolded FastAPI (or gated park) under `abassign1-greenfield\.agentic\` + inspectable Markdown/JSON |
| Brownfield | Security-oriented change path recorded under `abassign1\.agentic\` + `report` / `history` |
| Ambiguous | Clarification answers recorded; then plan/execution gates as documented |
| Packaging | Complete project at `..\abassign1`; CLI wheel/editable install from this repo only |

Acceptance: [SPEC.md](SPEC.md) AC-P6-1, AC-P6-2, AC-P6-3.
