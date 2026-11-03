# Manual test checklist (Phases 1–6)

Run all commands from the **CLI repo root** unless noted.  
Launcher: `python agenticli_test.py` (same commands work with `agentic` / `python -m agentic_engineer`).

Default LLM is **mock** (no API key). Optional live Anthropic: copy `agentic.config.example.toml` → `agentic.toml` and set `[llm]`.

**Gates in a full success path:** clarification (if needed) → spec → plan → command(s) → release → `completed`.

---

## Quick path (recommended — full autonomous E2E)

Uses a throwaway sibling target so you do not touch the Phase 6 seed.

```powershell
# A. Setup
.\.venv\Scripts\python.exe -m pip install -e ".[dev,anthropic]"
.\.venv\Scripts\python.exe -m pytest -q

# B. Fresh target + interactive through all gates
$t = "..\agentic-manual-e2e"
if (Test-Path $t) { Remove-Item -Recurse -Force $t }
New-Item -ItemType Directory -Path $t | Out-Null
python agenticli_test.py init $t
python agenticli_test.py run $t --interactive --requirement "Add a /health endpoint that returns status ok and the app version string"
```

At prompts (clear requirement — no clarification):

1. Spec — `a` + optional comment  
2. Plan — `a` + optional comment (execution starts automatically)  
3. Command — `a` when a test/shell command is proposed  
4. Release — `a` when parked at `awaiting_release_approval`

```powershell
python agenticli_test.py status $t
# expect: completed

python agenticli_test.py report $t
python agenticli_test.py history $t

# Inspect
# $t\.agentic\readable\SPECIFICATION.md / PLAN.md / REPORT.md / phases\
# $t\.agentic\reports\
# $t\.agentic\workflows\workflow_*\execution_history.json
# $t\.agentic\workflows\workflow_*\metrics.json
# $t\src\generated\  (mock developer outputs)
# $t\docs\AGENTIC_NOTES.md
```

Ambiguous path (clarification first):

```powershell
python agenticli_test.py init ..\agentic-manual-ambiguous --force
python agenticli_test.py run ..\agentic-manual-ambiguous -i -r "Improve sharing security"
# answer questions, then a/a/a/a through spec → plan → command → release
```

Phase 6 demo target (brownfield seed): follow [docs/phase6/DEMO.md](docs/phase6/DEMO.md) against `..\abassign1`.

---

## A. Setup

- [ ] Install

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,anthropic]"
```

- [ ] Automated tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expect: all passed, at most 1 skipped (symlink).

- [ ] LLM config (optional for live Anthropic; default is mock)

```powershell
copy agentic.config.example.toml agentic.toml
# edit agentic.toml → [llm] provider / model / api_key
```

---

## B. Phase 1 — init / isolation

- [ ] Init target

```powershell
python agenticli_test.py init ..\phase2-test-target
```

- [ ] Status on fresh target (no workflow yet)

```powershell
python agenticli_test.py status ..\phase2-test-target
```

- [ ] Refuse CLI self-target (must fail)

```powershell
python agenticli_test.py init .
```

---

## C0. Interactive end-to-end (recommended demo)

Prompts inline for clarification and each approval gate; work advances automatically between gates.

- [ ] Interactive run (long flag)

```powershell
python agenticli_test.py run ..\phase2-test-target --interactive --requirement "Improve sharing security"
```

- [ ] Interactive run (short flags)

```powershell
python agenticli_test.py run ..\phase2-test-target -i -r "Improve sharing security"
```

- [ ] Interactive run with requirement file

Create `requirement.md` first (see section D), then:

```powershell
python agenticli_test.py run ..\phase2-test-target --interactive --requirement-file .\requirement.md
```

At prompts:

1. Clarification — type each answer, Enter  
2. Spec gate — `a` / `r` / `c`, then optional comment  
3. Plan gate — same  
4. Command gate — approve proposed argv/shell  
5. Release gate — approve before successful `completed`

Example answers for the ambiguous requirement above:

```text
Require signed share links that expire in 24 hours
Must not break existing public reads
a
ok
a
plan ok
a
cmd ok
a
release ok
```

Expect final status: `completed` (after release). Intermediate: may show `plan_approved` then execution gates.

- [ ] Status after interactive run

```powershell
python agenticli_test.py status ..\phase2-test-target
```

- [ ] Report + history

```powershell
python agenticli_test.py report ..\phase2-test-target
python agenticli_test.py history ..\phase2-test-target
```

- [ ] Resume a parked workflow interactively (if you exited mid-gate)

```powershell
python agenticli_test.py run ..\phase2-test-target --interactive
```

- [ ] Interactive clear-requirement path (no clarification)

```powershell
python agenticli_test.py init ..\phase3-interactive-clear
python agenticli_test.py run ..\phase3-interactive-clear -i -r "Add a /health endpoint that returns status ok and the app version string"
```

At prompts: `a` for spec, plan, command, release.

- [ ] Interactive reject at spec gate (optional)

```powershell
python agenticli_test.py init ..\phase3-interactive-reject
python agenticli_test.py run ..\phase3-interactive-reject -i -r "Add a /health endpoint that returns status ok and the app version string"
```

At prompt: `r` then a comment. Expect status `spec_rejected`.

---

## C. Phase 2 — requirement (inline, non-interactive)

- [ ] Run with inline requirement

```powershell
python agenticli_test.py run ..\phase2-test-target --requirement "Improve sharing security"
```

- [ ] Status after run

```powershell
python agenticli_test.py status ..\phase2-test-target
```

---

## D. Phase 2 — requirement file (multiline)

Create `requirement.md` in the repo root (or any path):

```text
Improve sharing security.

Notes:
- Prefer expiring signed links
- Keep public reads working
```

- [ ] Run with requirement file

```powershell
python agenticli_test.py run ..\phase2-test-target --requirement-file .\requirement.md
```

Short flag:

```powershell
python agenticli_test.py run ..\phase2-test-target -R .\requirement.md
```

- [ ] With explicit config (optional)

```powershell
python agenticli_test.py --config .\agentic.toml run ..\phase2-test-target -R .\requirement.md
```

---

## E. Phase 2 — clarification → approve → inspect

Use after status shows `awaiting_clarification`:

- [ ] Provide answers

```powershell
python agenticli_test.py run ..\phase2-test-target --answer "Require signed share links that expire in 24 hours" --answer "Must not break existing public reads"
```

- [ ] Status (expect `awaiting_spec_approval`)

```powershell
python agenticli_test.py status ..\phase2-test-target
```

- [ ] Show specification

```powershell
python agenticli_test.py spec ..\phase2-test-target
```

- [ ] Approve specification (auto-advances into plan generation)

```powershell
python agenticli_test.py approve ..\phase2-test-target --comment "ok"
```

- [ ] Status after approve (expect `awaiting_plan_approval` — plan already generated)

```powershell
python agenticli_test.py status ..\phase2-test-target
```

- [ ] Spec again

```powershell
python agenticli_test.py spec ..\phase2-test-target
```

---

## F. Phase 2 — reject path (optional second target)

```powershell
python agenticli_test.py init ..\phase2-reject-target
python agenticli_test.py run ..\phase2-reject-target --requirement "Add a /health endpoint returning status and version"
python agenticli_test.py reject ..\phase2-reject-target --comment "rework"
python agenticli_test.py status ..\phase2-reject-target
```

---

## G. Phase 3 — plan gate → approve → execution starts

After spec approve, status should already be `awaiting_plan_approval` (plan auto-generated).

- [ ] Inspect plan graph (ASCII + Mermaid + parallel cohorts)

```powershell
python agenticli_test.py plan ..\phase2-test-target
```

- [ ] Approve plan (CLI auto-starts execution and parks at next gate)

```powershell
python agenticli_test.py approve ..\phase2-test-target --comment "plan ok"
```

Expect: `awaiting_command_approval` (or later gate), not a dead stop at `plan_approved`.

- [ ] Status

```powershell
python agenticli_test.py status ..\phase2-test-target
```

- [ ] Show plan again (no regeneration)

```powershell
python agenticli_test.py plan ..\phase2-test-target
python agenticli_test.py plan ..\phase2-test-target --json
```

Optional reject / changes-requested path on a second target:

```powershell
python agenticli_test.py init ..\phase3-plan-reject-target
python agenticli_test.py run ..\phase3-plan-reject-target --requirement "Add a /health endpoint returning status and version"
python agenticli_test.py approve ..\phase3-plan-reject-target --comment "spec ok"
python agenticli_test.py reject ..\phase3-plan-reject-target --comment "rework"
python agenticli_test.py status ..\phase3-plan-reject-target
```

---

## H. Phase 4 — execution (approve-before-run)

Use a fresh target (e.g. `..\phase4-fixture`) or continue after plan approval.

- [ ] Interactive through execution (spec → plan → command → release → completed)

```powershell
python agenticli_test.py init ..\phase4-fixture --force
python agenticli_test.py run ..\phase4-fixture --interactive --requirement "Add a /health endpoint that returns status ok and the app version string"
# approve spec, plan, command(s), then release
python agenticli_test.py status ..\phase4-fixture
```

Expect: `status: completed`; files under `src/generated/`; phase markdown past `06_`; `readable/REPORT.md`.

- [ ] Explicit gate path (non-interactive)

```powershell
# After plan approve, CLI already started execution → usually awaiting_command_approval
python agenticli_test.py approve ..\phase4-fixture --comment "run"
python agenticli_test.py status ..\phase4-fixture
# when awaiting_release_approval:
python agenticli_test.py approve ..\phase4-fixture --comment "ship"
```

If you stopped at `plan_approved` without the CLI auto-start (e.g. older session):

```powershell
python agenticli_test.py resume ..\phase4-fixture
```

- [ ] Command reject does not execute

```powershell
# At awaiting_command_approval:
python agenticli_test.py reject ..\phase4-fixture --comment "too risky"
```

Expect: no successful command evidence for that proposal; workflow may retry/safe-stop.

- [ ] Integration tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/ tests/unit/test_phase5_metrics_report.py -q
```

---

## I. Phase 5 — governance (report / history / revert refuse)

After a completed (or safe-stopped) workflow:

- [ ] Report

```powershell
python agenticli_test.py report ..\phase4-fixture
```

Expect: summary on stdout; `.agentic/reports/report_*.json` and `.agentic/readable/REPORT.md`; `workflows/*/metrics.json` derived from events only.

- [ ] History

```powershell
python agenticli_test.py history ..\phase4-fixture
```

Expect: events from `.agentic/workflows/*/execution_history.json`.

- [ ] File-level revert refused

```powershell
python agenticli_test.py revert ..\phase4-fixture
```

Expect: non-zero exit; message that only `resume` recovery is allowed.

---

## J. Phase 6 — demo target `..\abassign1`

Full scenarios: [docs/phase6/DEMO.md](docs/phase6/DEMO.md).

- [ ] Brownfield interactive (seed ShareApp)

```powershell
Remove-Item -Recurse -Force ..\abassign1\.agentic -ErrorAction SilentlyContinue
python agenticli_test.py init ..\abassign1
python agenticli_test.py run ..\abassign1 --interactive --requirement "Improve sharing security: private shares must not appear in GET /shares for anonymous callers; GET /shares/{token} for non-public shares must require an owner query parameter matching the share owner; keep public shares readable without auth."
python agenticli_test.py report ..\abassign1
```

- [ ] Target independence: from `..\abassign1`, run its own pytest / uvicorn without importing `agentic_engineer`.

---

## K. Inspect persisted artifacts

- [ ] Open on disk:

```text
..\phase2-test-target\.agentic\config.json
..\phase2-test-target\.agentic\specifications\
..\phase2-test-target\.agentic\plans\
..\phase2-test-target\.agentic\reports\
..\phase2-test-target\.agentic\readable\ANALYSIS.md
..\phase2-test-target\.agentic\readable\SPECIFICATION.md
..\phase2-test-target\.agentic\readable\PLAN.md
..\phase2-test-target\.agentic\readable\REPORT.md
..\phase2-test-target\.agentic\readable\phases\
..\phase2-test-target\.agentic\workflows\<id>\state.json
..\phase2-test-target\.agentic\workflows\<id>\approvals.json
..\phase2-test-target\.agentic\workflows\<id>\decisions.json
..\phase2-test-target\.agentic\workflows\<id>\execution_history.json
..\phase2-test-target\.agentic\workflows\<id>\metrics.json
..\phase2-test-target\.agentic\workflows\<id>\checkpoints\langgraph.sqlite
```

---

## Sign-off

| Field | Value |
| --- | --- |
| Tester | |
| Date | |
| Result | Pass / Fail |
| Notes | |
