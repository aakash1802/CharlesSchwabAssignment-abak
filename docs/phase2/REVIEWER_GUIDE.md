# Phase 2 Reviewer Guide

## Setup

From the CLI repository root:

```text
python -m pip install -e ".[dev]"
pytest -q
```

Expect: tests passed with at most 1 skip (symlink-related on some Windows setups).

Optional live Anthropic (not required for CI): see [LLM_CONFIGURATION.md](LLM_CONFIGURATION.md).

## Reproduce ambiguous → approved path

Use any directory **outside** this repository (sibling folder or temp path).

```text
agentic init ../phase2-review-target
agentic run ../phase2-review-target --requirement "Improve sharing security"
agentic status ../phase2-review-target
agentic run ../phase2-review-target --answer "Require signed share links that expire in 24 hours" --answer "Must not break existing public read links"
agentic approve ../phase2-review-target --comment "Reviewer acceptance"
agentic spec ../phase2-review-target
agentic status ../phase2-review-target
```

### What to inspect on disk

```text
../phase2-review-target/.agentic/config.json
../phase2-review-target/.agentic/specifications/spec_*.json
../phase2-review-target/.agentic/workflows/workflow_*/state.json
../phase2-review-target/.agentic/workflows/workflow_*/approvals.json
```

Compare with checked-in samples under [sample_artifacts/](sample_artifacts/).

## Reproduce rejection path

```text
agentic init ../phase2-reject-target
agentic run ../phase2-reject-target --requirement "Add a /health endpoint returning status and version"
agentic reject ../phase2-reject-target --comment "Needs version format defined"
agentic status ../phase2-reject-target
```

Expect `status: spec_rejected`.

## Negative control (isolation)

```text
agentic init .
```

Expect non-zero exit and a refusal to use the CLI repository as a target.

## Review focus questions

1. Is the ambiguity gate visible and blocking before a silent assumption?
2. Is the specification readable without reading Python source?
3. Does `approvals.json` show a human decision with timestamp/comment?
4. Did anything land inside the CLI repo that looks like a target app? (Should be no.)
