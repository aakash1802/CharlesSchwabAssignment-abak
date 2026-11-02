# Phase 2 Delivery Report

**Product:** Agentic Engineer CLI  
**Boundary:** Phase 2 — Requirement intelligence  
**Date captured:** 2026-11-02  
**Status:** Implemented and under lead test/stabilize pause (Phases 3+ deferred)

---

## 1. Objective delivered

Convert a natural-language requirement for a **target project** into:

1. Structured requirement analysis (with ambiguity detection).
2. Optional clarification answers.
3. A reviewable specification persisted under the target’s `.agentic/`.
4. A human approval or rejection record (deterministic governance).

This is a vertical slice of the approved architecture’s intelligence + governance + persistence layers. It does **not** implement planning or code execution (Phases 3–4).

---

## 2. Inputs and outputs

### Inputs

| Input | Mechanism |
| --- | --- |
| Target project path | CLI argument on all commands |
| Requirement text | `agentic run <path> --requirement "..."` |
| Clarification answers | `agentic run <path> --answer "..." [--answer "..."]` |
| Human decision | `agentic approve` / `agentic reject` (+ optional `--comment`) |
| LLM mode | `AGENTIC_LLM_PROVIDER=mock\|anthropic` — see [LLM_CONFIGURATION.md](LLM_CONFIGURATION.md) |

### Outputs

| Output | Location / command |
| --- | --- |
| Workspace bootstrap | `<target>/.agentic/` via `agentic init` |
| Workflow state (analysis, answers, status) | `.agentic/workflows/<id>/state.json` |
| Approval history | `.agentic/workflows/<id>/approvals.json` |
| Specification document | `.agentic/specifications/spec_*.json` + `agentic spec` |
| Operator-visible status | `agentic status` |

### Terminal workflow statuses (Phase 2)

`analyzing` → `awaiting_clarification` → `generating_spec` → `awaiting_spec_approval` → `spec_approved` | `spec_rejected` | `stopped` (changes requested)

---

## 3. Module map (implementation)

```text
src/agentic_engineer/
  cli/main.py                         # init, run, status, spec, approve, reject
  config/settings.py                  # AGENTIC_* settings
  models/
    requirements.py                   # analysis + clarification models
    specification.py                  # Specification
    approval.py                       # ApprovalRecord / decisions
    workflow.py                       # RequirementWorkflowState
  agents/
    requirement_analyzer.py           # analyzer (+ deterministic mock path)
    specification_generator.py        # spec generator (+ deterministic mock path)
    prompts/*.txt                     # prompt texts separated from logic
  governance/approvals.py             # human-only decisions
  persistence/
    json_store.py                     # atomic JSON writes
    spec_store.py
    workflow_store.py
  graph/
    nodes_requirement.py              # shared analyze/spec node helpers
    requirement_graph.py              # LangGraph routing (in-process)
    requirement_workflow.py           # persisted CLI workflow service
  workspace/                          # Phase 1 isolation (still enforced)
  llm/                                # provider protocol + MockProvider + AnthropicProvider
```

### Architectural alignment

| Layer | Phase 2 realization |
| --- | --- |
| Intelligence | RequirementAnalyzer, SpecificationGenerator |
| Orchestration | RequirementWorkflowService + LangGraph routing graph |
| Execution | Workspace + JsonStore only (no shell/code gen yet) |
| Governance | ApprovalService; CLI approve/reject |

---

## 4. Persistence layout (target-owned)

```text
<target>/
  .agentic/
    config.json
    specifications/spec_<id>.json
    workflows/workflow_<id>/
      state.json
      approvals.json
    plans/ artifacts/ reports/          # reserved for later phases
```

Sample captured run: [sample_artifacts/](sample_artifacts/)  
Example IDs from audit demo: `workflow_c52cf4d8170e`, `spec_e61785ae63`, `appr_2d93c87c50`.

---

## 5. Test evidence

Command:

```text
python -m pip install -e ".[dev]"
pytest -q
```

Result (also in [pytest_results.txt](pytest_results.txt)):

```text
33 passed, 1 skipped
```

| Area | Tests |
| --- | --- |
| Workspace isolation (Phase 1) | `test_workspace_*.py`, `test_cli_init.py` |
| JSON persistence | `test_json_store.py` |
| Mock LLM | `test_llm_mock.py` |
| Anthropic provider (mocked SDK) | `test_llm_anthropic.py` |
| Ambiguity / clear analysis | `test_requirement_analyzer.py` |
| Workflow + approvals | `test_requirement_workflow.py` |
| LangGraph routing | `test_requirement_graph.py` |
| CLI end-to-end Phase 2 | `test_cli_requirement.py` |

Skipped: symlink-escape test when the OS cannot create symlinks.

---

## 6. Manual audit demo (executed)

Requirement: `Improve sharing security` (ambiguous).

1. `agentic init <temp-target>`
2. `agentic run … --requirement "Improve sharing security"` → `awaiting_clarification`
3. `--answer` ×2 → `awaiting_spec_approval` + spec file written
4. `agentic approve --comment "Approved for Phase 2 audit sample"` → `spec_approved`
5. Artifacts copied to `docs/phase2/sample_artifacts/`

---

## 7. Limitations (intentional)

- No task planner / dependency graph (Phase 3).
- No Developer/Testing agents or file codegen (Phase 4).
- Live Anthropic calls require `.[anthropic]` install + API key; CI remains on mock.
- CLI resume uses JSON workflow state; full LangGraph checkpointer resume is Phase 4.
- No demo target application in this repository.
- **Do not re-implement LLM providers in Phases 3–6** — extend `LLMProvider` only if a new backend is needed.

---

## 8. Resume point for later phases

When the lead reopens Phase 3, start from an **approved specification** (`status=spec_approved`) already stored under `.agentic/specifications/`. Phase 2 contracts do not need to be rewritten for planning to begin.
