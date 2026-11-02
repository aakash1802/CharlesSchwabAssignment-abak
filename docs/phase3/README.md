# Phase 3 audit package

Planning and dependency graph delivery notes for the Agentic Engineer CLI.

## Scope

Approved specification → **automatic** task plan generation + deterministic validation (cycles, missing refs, ready-set, parallel cohorts) → plan approval gate → human-readable `PLAN.md`.

Human interrupts remain only at clarification and approval gates. Generation/validation advances without a separate `plan` command after spec approve.

## Commands

```text
agentic approve <target>   # spec gate → auto plan → awaiting_plan_approval
agentic plan <target>      # inspect graph (or --generate after plan reject)
agentic approve <target>   # plan gate
agentic status <target>
```

## Artifacts

| Path | Role |
| --- | --- |
| `.agentic/plans/plan_*.json` | Machine-readable plan |
| `.agentic/readable/PLAN.md` | Reviewer Markdown (ASCII + Mermaid + cohorts) |
| `.agentic/readable/phases/05_plan.md` | Phase summary |
| `.agentic/readable/phases/06_plan_approval.md` | Plan gate decision |

## Tests

```text
pytest tests/unit/test_dependency_validation.py
pytest tests/unit/test_task_planner.py
pytest tests/unit/test_plan_workflow.py
pytest tests/unit/test_cli_plan.py
```

## Out of scope

Task execution, LangGraph checkpointer resume, Developer/Testing agents — Phase 4.
