# Manual test checklist (Phases 1–3)

Run all commands from the **CLI repo root** unless noted.  
Launcher: `python agenticli_test.py` (same commands work with `agentic` / `python -m agentic_engineer`).

Target used below: `..\phase2-test-target` (must be **outside** this repo).

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

## C. Phase 2 — requirement (inline)

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

## G. Phase 3 — plan gate → approve → show graph

After spec approve, status should already be `awaiting_plan_approval` (plan auto-generated).

- [ ] Inspect plan graph (ASCII + Mermaid + parallel cohorts)

```powershell
python agenticli_test.py plan ..\phase2-test-target
```

- [ ] Approve plan

```powershell
python agenticli_test.py approve ..\phase2-test-target --comment "plan ok"
```

- [ ] Status (expect `plan_approved`)

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

## H. Inspect persisted artifacts

- [ ] Open on disk:

```text
..\phase2-test-target\.agentic\config.json
..\phase2-test-target\.agentic\specifications\
..\phase2-test-target\.agentic\plans\
..\phase2-test-target\.agentic\readable\ANALYSIS.md
..\phase2-test-target\.agentic\readable\SPECIFICATION.md
..\phase2-test-target\.agentic\readable\PLAN.md
..\phase2-test-target\.agentic\readable\phases\
..\phase2-test-target\.agentic\workflows\<id>\state.json
..\phase2-test-target\.agentic\workflows\<id>\approvals.json
```

---

## Sign-off

| Field | Value |
| --- | --- |
| Tester | |
| Date | |
| Result | Pass / Fail |
| Notes | |
