# Sample `.agentic` artifacts (Phase 2 audit)

Captured from a live CLI run on 2026-11-02 against a temporary target.

| Field | Value |
| --- | --- |
| Requirement | `Improve sharing security` |
| Workflow | `workflow_c52cf4d8170e` |
| Specification | `spec_e61785ae63` |
| Approval | `appr_2d93c87c50` → `approved` |
| Final status | `spec_approved` |

Tree:

```text
.agentic/
  config.json
  specifications/spec_e61785ae63.json
  workflows/workflow_c52cf4d8170e/
    state.json
    approvals.json
  plans/ artifacts/ reports/   # empty placeholders for later phases
```

These files are **review fixtures**, not runtime dependencies of the CLI.
