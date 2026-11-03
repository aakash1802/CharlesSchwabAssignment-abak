# Agentic Engineer — user manual

Manual for a person installing, running, and assessing this project. It covers setup, every CLI command, the files the CLI writes, workflow statuses, and the conventions that define a correct run.

This repository is the **CLI only** (`agentic-engineer` 0.1.0). It creates, modifies, tests, and documents a **separate target project**. Target application source never lives in this tree.

Companion docs (deeper design, not required to operate the CLI):

| Document | Use it for |
| --- | --- |
| [README.md](README.md) | Short status and layout |
| [TEST_CHECKLIST.md](TEST_CHECKLIST.md) | Checkbox script for a full manual pass |
| [docs/phase6/DEMO.md](docs/phase6/DEMO.md) | Greenfield, brownfield, and ambiguous demo against `../abassign1` |
| [docs/phase2/LLM_CONFIGURATION.md](docs/phase2/LLM_CONFIGURATION.md) | Mock vs Anthropic configuration |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Product scope and acceptance criteria |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design |
| [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) | Recorded trade-offs |

Commands below use Windows PowerShell from the CLI repo root. On macOS or Linux, use the same arguments with `/` paths and `python3` if that is the 3.11+ interpreter.

---

## 1. What you are assessing

Agentic Engineer is a standalone software-engineering CLI. Given a natural-language requirement and a target directory, it:

1. Analyzes the requirement and asks essential clarification questions when the text is ambiguous.
2. Writes a reviewable specification and waits for a human decision.
3. Builds an engineering task plan with an explicit dependency graph and waits again.
4. Executes tasks with specialized agents (design, code, tests, documentation).
5. Proposes shell or argv commands and **does not run them** until a human approves.
6. Writes an engineering report and waits for release approval before marking the workflow complete.
7. Records every gate, command, and recovery attempt under the target’s `.agentic/` directory.

The language model never approves its own work. Approval, rejection, and clarification answers come only from the operator (interactive prompts or explicit CLI flags).

### Two directories

```text
PycharmProjects/
├── CharlesSchwabAssignment-abak/   ← this repo = the CLI
└── abassign1/                      ← Phase 6 demo target (FastAPI ShareApp)
    └── .agentic/                   ← created by the CLI; workflow metadata only
```

`abassign1` is a sibling, outside this repository. A throwaway directory such as `../agentic-manual-e2e` is safer for a first assessment so the seed app is left intact.

### What a successful assessment shows

| Check | Pass condition |
| --- | --- |
| Install | `pip install -e ".[dev]"` and `pytest` succeed on Python 3.11+ |
| Isolation | `agentic init` refuses this repository as a target |
| Independence | The target app does not depend on `agentic-engineer` or `agentic_engineer` |
| Workflow | A requirement moves through the gates below and ends in a documented status |
| Audit | `.agentic/` contains JSON state plus human-readable Markdown |
| Commands | Proposed commands appear as `pending_command` and run only after `approve` |

Default provider is **`mock`**: deterministic stubs, no network, suitable for offline review. Live file generation uses **`anthropic`** (section 4).

---

## 2. Installation

### Prerequisites

- Python **3.11 or newer** (`python --version`)
- `pip`
- A directory **outside** this repo to use as the target
- Optional: an Anthropic API key only if you want live model output

### Create a virtual environment (recommended)

From the CLI repository root (`CharlesSchwabAssignment-abak`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Live Anthropic as well as tests:

```powershell
python -m pip install -e ".[dev,anthropic]"
```

`[all]` is the same pair: pytest and the Anthropic SDK.

Confirm:

```powershell
python -m pytest -q
python agenticli_test.py version
```

`version` prints `0.1.0`. Pytest should pass. At most one test may skip (symlink behavior on Windows).

`.venv/` is local tooling. Do not treat it as source and do not commit it.

### Three ways to launch the same CLI

All three call the same Typer app.

| Launcher | When to use it |
| --- | --- |
| `python agenticli_test.py …` | Local testing. Adds `src/` to `sys.path`, so it works even before an editable install. **Preferred in this repo’s docs.** |
| `agentic …` | Console script installed by `pip install -e .` (`[project.scripts]` in `pyproject.toml`). |
| `python -m agentic_engineer …` | Module entry (`src/agentic_engineer/__main__.py`). |

Global flags apply **before** the subcommand:

```powershell
python agenticli_test.py --verbose --config .\agentic.toml status ..\abassign1
python agenticli_test.py -v -c .\agentic.toml version
```

| Flag | Meaning |
| --- | --- |
| `--verbose` / `-v` | Debug logging for this process |
| `--config` / `-c PATH` | TOML settings file. Must be a file path. Missing file exits with code 1 |

Help:

```powershell
python agenticli_test.py --help
python agenticli_test.py run --help
```

---

## 3. Project conventions

These rules are enforced in code, not only in prompts.

### Isolation

- The target must be a directory **outside** this repository and outside the installed `agentic_engineer` package.
- `init` or `open` on this repo (or any nested path) raises an isolation error and the CLI exits with **code 3**.
- File writes are resolved under the target root. `..` traversal and symlink escapes that leave the root are rejected.
- The target application must keep running with its own virtual environment. It must not import this CLI. After a demo, search the target’s `pyproject.toml` and `requirements.txt` for `agentic-engineer` or `agentic_engineer` and expect no matches.
- Do not copy `abassign1` source into this repository, and do not copy CLI implementation into a target.

### Human gates

A full success path is:

```text
requirement
  → clarification (only if the analyzer marks essential questions)
  → specification approval
  → plan approval
  → command approval (one or more; approve-before-run)
  → optional destructive-action approval
  → release approval
  → status completed
```

Rejecting a spec, plan, command, destructive action, or release records the decision and stops or parks the workflow. The model cannot set `decision=approved`.

### Commands

Any argv or shell string may be **proposed**. Nothing runs until a human approves that exact proposal. Working directory must stay inside the target. Default command timeout is 120 seconds (`command_timeout_seconds`). Stdout and stderr stored as evidence are truncated at 8000 characters.

`agentic revert` does **not** roll back files. Recovery of an in-flight graph is checkpoint resume (`agentic resume`), not file-level undo.

### Metadata vs application source

Everything the CLI owns on the target lives under `.agentic/`. Application files the agents write (for example `src/generated/…` or `docs/AGENTIC_NOTES.md`) are ordinary project files. Deleting `.agentic/` resets workflow state and leaves application files in place.

### Secrets

- Never commit `.env`, `agentic.toml`, `agentic.config.toml`, or API keys.
- Those names are gitignored. `agentic.config.example.toml` is the committed template and contains a placeholder key only.
- Approval comments are stored in the target’s `.agentic/` tree. Do not put secrets in comments.

### Identifiers

| Kind | Pattern | Example |
| --- | --- | --- |
| Workflow | `workflow_` + 12 hex chars | `workflow_a1b2c3d4e5f6` |
| Specification | `spec_` + 10 hex chars | `spec_a1b2c3d4e5` |
| Plan | `plan_` + 10 hex chars | `plan_a1b2c3d4e5` |
| Approval | `appr_` + 10 hex chars | `appr_a1b2c3d4e5` |
| Command proposal | `cmd_` + 10 hex chars | `cmd_a1b2c3d4e5` |
| Recovery attempt | `rec_` + 12 hex chars | `rec_a1b2c3d4e5f6` |

Persisted models use `schema_version: 1`. Timestamps are UTC.

### One active workflow

`.agentic/config.json` points at a single `active_workflow_id`, `active_specification_id`, and `active_plan_id`. Starting a new requirement replaces the active pointer. Older workflow directories under `.agentic/workflows/` remain on disk.

### Providers

Phases 3–6 reuse the Phase 2 provider (`mock` or `anthropic`) via `build_provider()`. There is no second LLM stack. With the default mock provider and no queued responses, agents write deterministic stubs (a small Python file per task under `src/generated/`, a test command that prints `test-ok:<task id>`, and `docs/AGENTIC_NOTES.md`). With Anthropic configured, the same agents ask the model for real files and real test commands, still behind the same human gates.

### Mock vs live when you assess

| Provider | What you can conclude |
| --- | --- |
| `mock` (default) | Orchestration, gates, persistence, reports, and isolation. Generated application code is a stub, not a product change. |
| `anthropic` | The same control flow, plus model-written files and proposed test commands. Quality of the code is model output and still requires the release gate. |

State this explicitly in an assessment. A green `completed` status on `mock` proves the workflow, not that ShareApp’s security changed.

---

## 4. Configuration

Settings are process-wide. They are **not** stored in the target’s `.agentic/config.json`.

### Precedence (highest wins)

1. Values passed in code / CLI `--config` file selection (the file itself is a source, not an override of env)
2. Environment variables prefixed with `AGENTIC_`
3. `.env` in the current working directory
4. TOML config file
5. Built-in defaults

Practical reading order for the TOML **file**:

1. `--config path\to\file.toml` (or `-c`)
2. `AGENTIC_CONFIG` (path to a TOML file)
3. `./agentic.toml` or `./agentic.config.toml` in the current working directory
4. `%USERPROFILE%\.agentic\config.toml`

If `--config` names a missing file, the CLI exits with code 1.

Environment and `.env` override keys loaded from TOML. A key set only in `agentic.toml` is used when the environment does not set it.

### Recommended local file

```powershell
copy agentic.config.example.toml agentic.toml
```

Edit `agentic.toml` (gitignored):

```toml
log_level = "INFO"

[llm]
provider = "anthropic"          # or "mock"
model = "claude-sonnet-5-5"
api_key = "sk-ant-..."
timeout_seconds = 60
max_tokens = 4096

[execution]
max_task_retries = 2
command_timeout_seconds = 120
```

Leave `provider = "mock"` (or omit the file) for an offline assessment.

### Environment variables

Copy `.env.example` to `.env` if you prefer env files. Common variables:

| Variable | Default | Role |
| --- | --- | --- |
| `AGENTIC_LOG_LEVEL` | `INFO` | Logging level (`--verbose` forces DEBUG) |
| `AGENTIC_CONFIG` | (unset) | Path to a TOML file |
| `AGENTIC_LLM_PROVIDER` | `mock` | `mock` or `anthropic` |
| `AGENTIC_LLM_MODEL` | `mock-model` | For Anthropic, empty or `mock-model` becomes `claude-sonnet-5-5` |
| `AGENTIC_LLM_API_KEY` | (unset) | Provider key. If empty, `ANTHROPIC_API_KEY` is used |
| `AGENTIC_LLM_TIMEOUT_SECONDS` | `60` | Per-request timeout |
| `AGENTIC_LLM_MAX_TOKENS` | `4096` | Response token cap |
| `AGENTIC_MAX_TASK_RETRIES` | `2` | Ordinary task retry cap |
| `AGENTIC_MAX_STRUCTURED_RETRIES` | `2` | Cap for structured-output / truncation failures |
| `AGENTIC_MAX_SAME_RETRIES` | `2` | Recovery budget: retry the same operation |
| `AGENTIC_MAX_CORRECTED_RETRIES` | `2` | Recovery budget: retry with corrected inputs |
| `AGENTIC_MAX_SCOPE_REDUCTIONS` | `2` | Recovery budget: shrink the task |
| `AGENTIC_MAX_REPLANS` | `1` | Recovery budget: replan (returns to plan approval) |
| `AGENTIC_MAX_TOTAL_RECOVERY_ATTEMPTS` | `5` | Total automatic recovery attempts per task |
| `AGENTIC_DEVELOPER_MAX_FILES_PER_BATCH` | `5` | Files emitted per Developer Agent batch |
| `AGENTIC_DEVELOPER_MAX_BATCHES` | `4` | Batches per task |
| `AGENTIC_DEVELOPER_STRUCTURED_ATTEMPTS` | `2` | Regenerations inside one batch |
| `AGENTIC_COMMAND_TIMEOUT_SECONDS` | `120` | Approved-command timeout |

Budgets are enforced in Python. The model cannot raise them.

---

## 5. Operating concepts

### Target path

Every command except `version` takes a project path as the first argument. Relative paths resolve from the current working directory. The directory must already contain `.agentic/` except for `init`, which creates it.

```powershell
python agenticli_test.py init ..\abassign1 --force
python agenticli_test.py status ..\abassign1
```

### Interactive session vs explicit gates

**Interactive** (`run --interactive` or `-i`) stays in one terminal. It auto-advances analysis, spec generation, plan generation, and execution, and stops only to ask you for:

- clarification answers (empty answers are rejected)
- approve / reject / changes-requested

At a gate the prompt is:

```text
Choose: [a]pprove / [r]eject / [c]hanges-requested
Decision:
Comment (optional):
```

Accepted words: `a`/`approve`/`yes`/`y`, `r`/`reject`/`no`/`n`, `c`/`changes`/`changes-requested`.

**Explicit** (no `--interactive`) is better when you want to inspect files between steps or script the assessment:

```powershell
python agenticli_test.py run <path> --requirement "..."
python agenticli_test.py status <path>
python agenticli_test.py spec <path>
python agenticli_test.py approve <path> --comment "spec ok"
python agenticli_test.py plan <path>
python agenticli_test.py approve <path> --comment "plan ok"
# execution starts; usually parks at awaiting_command_approval
python agenticli_test.py approve <path> --comment "run tests"
# repeat approve for further command gates and for release
python agenticli_test.py report <path>
```

Do not combine `--requirement` with `--answer`, or `--answer` with `--interactive`.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Command finished and printed status or the requested artifact |
| 1 | Workflow or workspace error (missing `.agentic/`, empty requirement, no spec yet, invalid combination of flags, `revert`) |
| 2 | Target directory is not empty and `init` was called without `--force` |
| 3 | Target is this CLI repository or sits inside it |

---

## 6. Command reference

Replace `<path>` with the target directory, for example `..\abassign1` or `..\agentic-manual-e2e`.

### `version`

```powershell
python agenticli_test.py version
```

Prints `0.1.0`. No target path.

### `init`

```powershell
python agenticli_test.py init <path>
python agenticli_test.py init <path> --force
```

Creates the target directory if needed and creates `.agentic/` (layout in section 8).

| Situation | Behavior |
| --- | --- |
| Path does not exist | Directory and `.agentic/` are created |
| Empty directory, or only `.git`, `.DS_Store`, `Thumbs.db` | Initializes with no extra flag |
| Non-empty and not yet initialized | Exits code 2. Re-run with `--force`, `--yes`, or `-y` |
| Already initialized | Refreshes `updated_at` in `.agentic/config.json`. Safe to repeat |
| Path is a file | Error, exit 1 |
| Path is inside this repo | Error, exit 3 |

`--force` does not delete existing application files. It only allows `.agentic/` to be created beside them.

### `run`

Starts or continues the workflow.

```powershell
# New workflow from a one-line requirement
python agenticli_test.py run <path> --requirement "Improve sharing security"
python agenticli_test.py run <path> -r "Improve sharing security"

# New workflow from a multiline file (this repo’s requirement.md is an example)
python agenticli_test.py run <path> --requirement-file .\requirement.md
python agenticli_test.py run <path> -R .\requirement.md

# Continue after awaiting_clarification (one --answer per essential question, in order)
python agenticli_test.py run <path> --answer "Private shares need an owner query param" --answer "Keep public reads"

# One session: prompts for answers and every gate
python agenticli_test.py run <path> --interactive --requirement "Make sharing better and safer somehow"
python agenticli_test.py run <path> -i
```

| Flag | Effect |
| --- | --- |
| `--requirement` / `-r` | Start a **new** workflow with this text |
| `--requirement-file` / `-R` | Start a **new** workflow from a UTF-8 text or Markdown file. File must exist and be non-empty after stripping |
| `--answer` / `-a` | Repeatable. Supplies clarification answers and continues. Count should match essential questions |
| `--interactive` / `-i` | Prompt through remaining human gates. With no requirement, resumes the active workflow |

`run` without a requirement, without `--answer`, and without `--interactive`:

- If status is `plan_approved` or `executing`, starts or continues execution until the next human gate.
- If a command, destructive, or release gate is already pending, it errors and tells you to use `--interactive` or `approve` / `reject`.
- Otherwise it errors and tells you how to start.

On success it prints the workflow status block (section 7).

### `status`

```powershell
python agenticli_test.py status <path>
```

Always prints workspace root, `schema_version`, and the active workflow, specification, and plan ids (`(none)` if unset).

If there is no active workflow:

```text
phase: initialized (no active workflow)
```

Otherwise it prints the same status block as `run` (section 7), including paths to readable Markdown when those files exist.

### `spec`

```powershell
python agenticli_test.py spec <path>
python agenticli_test.py spec <path> --json
```

Prints `.agentic/readable/SPECIFICATION.md` when that file exists. `--json` prints the specification model. Exit code 1 and a yellow message if no specification has been generated yet (still in analysis or clarification).

### `plan`

```powershell
python agenticli_test.py plan <path>
python agenticli_test.py plan <path> --json
python agenticli_test.py plan <path> --generate
```

Shows or generates the task plan. Prints the status block, then an ASCII dependency graph plus a Mermaid copy. `--json` prints the plan model instead of the graph. `--generate` / `-g` forces regeneration when the current status allows it.

`PLAN.md` on disk is the review copy. The command output is the live graph, which is what you should read at the plan gate.

### `approve`

```powershell
python agenticli_test.py approve <path>
python agenticli_test.py approve <path> --comment "looks right"
python agenticli_test.py approve <path> -c "looks right"
```

Records an **approved** decision for the single pending gate. What happens next depends on the status **before** the call:

| Status before | Result |
| --- | --- |
| `awaiting_spec_approval` | Spec approved. Plan is generated and the workflow parks at `awaiting_plan_approval` |
| `awaiting_plan_approval` | Plan approved. Execution starts immediately and runs until the next human gate (usually `awaiting_command_approval`) |
| `awaiting_command_approval` | The pending command runs inside the target. Execution continues |
| `awaiting_destructive_approval` | The destructive proposal is recorded as approved. In the current slice the action is recorded and not applied as a raw delete |
| `awaiting_release_approval` | Workflow becomes `completed` |

There is no `--type` flag. The pending gate is implied by status. Calling `approve` with nothing pending is an error.

### `reject`

```powershell
python agenticli_test.py reject <path> --comment "needs auth model"
python agenticli_test.py reject <path> --changes-requested --comment "split the tasks"
```

Records `rejected`, or `changes_requested` when `--changes-requested` is set. The CLI prints which gate was decided (Specification, Plan, Command, Destructive action, or Release) and the resulting status.

Use reject when you want the assessment to show a negative path. A rejected command is not executed; evidence says the human rejected it.

### `resume`

```powershell
python agenticli_test.py resume <path>
```

Continues execution from the LangGraph checkpoint (`checkpoints/langgraph.sqlite`) when you left mid-flight **without** a pending human gate. If a gate is pending, use `approve` or `reject` (or `run --interactive`) instead. Resume does not skip approvals.

### `report`

```powershell
python agenticli_test.py report <path>
```

Builds the engineering report from the audit log (it does not invent metrics), writes:

- `.agentic/reports/report_<workflow_id>.json`
- `.agentic/readable/REPORT.md`
- `.agentic/workflows/<workflow_id>/metrics.json`

and prints a short summary: status line, event counts, retries, replans, safe stops, and the two report paths. You can run `report` before release (for example while parked at `awaiting_release_approval`) and again after `completed`.

### `history`

```powershell
python agenticli_test.py history <path>
```

Prints the append-only audit log for the active workflow: timestamp, event type, optional task id, and message. Source file: `.agentic/workflows/<workflow_id>/execution_history.json`. If that file is missing, an older `execution_events.json` is read.

### `revert`

```powershell
python agenticli_test.py revert <path>
```

Always refuses file-level revert and exits with code 1. The message tells you to use checkpoint resume. This command exists so an assessor can see the policy, not as an undo button.

---

## 7. Reading `status` output

Example shape (fields appear only when they apply):

```text
root: C:\Users\Avita\PycharmProjects\abassign1
schema_version: 1
active_workflow_id: workflow_abc123def456
active_specification_id: spec_abc123def4
active_plan_id: plan_abc123def4
workflow_id: workflow_abc123def456
status: awaiting_command_approval
requirement: Improve sharing security
specification_id: spec_abc123def4
plan_id: plan_abc123def4
execution_thread_id: workflow_abc123def456
current_cohort: task_2, task_3
tasks:
  - task_1: completed
  - task_2: in_progress
pending_command: python -c print('test-ok:task_2')
pending_approval_id: appr_abc123def4
readable_dir: ...\.agentic\readable
readable_spec: ...\.agentic\readable\SPECIFICATION.md
readable_plan: ...\.agentic\readable\PLAN.md
```

### Workflow statuses

| Status | Meaning | What you do |
| --- | --- | --- |
| `analyzing` | Requirement analyzer is running | Wait; normally not a park point |
| `awaiting_clarification` | Essential questions are unanswered | `run --answer "..." ...` or `run -i`. Status lists each `[question id]` |
| `generating_spec` | Specification is being written | Wait |
| `awaiting_spec_approval` | Spec is ready | Read `spec` output or `SPECIFICATION.md`, then `approve` or `reject` |
| `spec_approved` | Spec accepted; plan generation did not finish | `plan <path> --generate`, or `run -i` (interactive retries plan generation) |
| `spec_rejected` | Spec gate rejected (`reject` without `--changes-requested`) | Terminal for this pass. Inspect `phases/04_approval.md`. Start a new `run --requirement` if you want another attempt |
| `planning` | Task planner is running | Wait |
| `awaiting_plan_approval` | Plan and dependency graph are ready | Read `plan` output, then `approve` or `reject` |
| `plan_approved` | Plan accepted; execution not started | `approve` on the plan gate starts execution. If you already approved and then exited before execution, `run` or `resume` starts it. Status text also suggests `run -i` or `resume` |
| `plan_rejected` | Plan gate rejected (`reject` without `--changes-requested`) | Terminal for this pass. Inspect `phases/06_plan_approval.md` |
| `executing` | Agents are running between gates | `resume` or `run` if the process was interrupted here |
| `awaiting_command_approval` | A command is proposed and has not run | Read `pending_command`. `approve` runs it. `reject` records refusal and does not run it |
| `awaiting_destructive_approval` | A destructive file action is proposed | Read `pending_destructive` (action and paths). `approve` or `reject` |
| `awaiting_release_approval` | Execution finished the success path | Read `report` and `history`, then `approve` to complete or `reject` to withhold release |
| `completed` | Release was approved | Read `report`. This is the success terminal state |
| `safe_stopped` | Automatic recovery budget was exhausted or a failure was escalated | Read `stop_reason` and the red `failure_summary` (task id, name, error). This is a controlled stop, not a crash of the CLI |
| `stopped` | Spec or plan gate recorded `changes_requested` | Read `stop_reason` (`Specification changes requested` or `Plan changes requested`). Terminal for this pass |

Task lines during execution use: `pending`, `ready`, `in_progress`, `completed`, `failed`, `blocked`. A non-zero `retries=` and `error=` are printed when set.

`current_cohort` is the set of tasks the scheduler is running together (tasks whose dependencies are satisfied and that do not depend on each other).

### Clarification

Only questions marked essential block the workflow. Status prints them as:

```text
clarification_questions:
  - [q1] ...
```

Answers are stored on the workflow and copied into `.agentic/readable/phases/02_clarification.md`. Pass `--answer` once per essential question, in the order printed.

---

## 8. Files on the target (`.agentic/`)

`init` creates this tree:

```text
<target>/
└── .agentic/
    ├── config.json
    ├── specifications/          # spec_<id>.json and spec_<id>.md
    ├── plans/                   # plan_<id>.json and plan_<id>.md
    ├── workflows/
    │   └── workflow_<id>/       # created when a run starts
    ├── artifacts/
    ├── reports/                 # written by `report`
    └── readable/
        └── phases/
```

`artifacts/` is reserved layout. Workflow truth lives in the other directories.

### `.agentic/config.json`

Workspace pointer, not LLM settings.

| Field | Meaning |
| --- | --- |
| `schema_version` | `1` |
| `created_at`, `updated_at` | UTC timestamps. `init` on an existing workspace refreshes `updated_at` |
| `active_workflow_id` | Workflow that `status`, `spec`, `plan`, `approve`, `report`, and `history` use |
| `active_specification_id` | Current spec id, or null |
| `active_plan_id` | Current plan id, or null |
| `notes` | Optional operator note; usually null |

### Per-workflow directory

`.agentic/workflows/workflow_<id>/`

| File | Written by | Contents |
| --- | --- | --- |
| `state.json` | Workflow engine | Full `RequirementWorkflowState`: requirement text, status, analysis, clarification answers, embedded spec and plan, pending command or destructive proposal, test evidence, stop reason, execution thread id |
| `approvals.json` | Approval service | Every gate request and decision (`pending`, `approved`, `rejected`, `changes_requested`) with type `specification`, `plan`, `command`, `destructive`, or `release` |
| `decisions.json` | Approval service | Decided approvals mirrored for lineage. Pending rows stay in `approvals.json` until decided |
| `execution_history.json` | Audit log | Append-only `{ "events": [ ... ] }`. `history` and `report` read this. Legacy name `execution_events.json` is still readable |
| `metrics.json` | `report` | Counts derived only from events. Missing categories are listed under `insufficient_data` instead of being filled in |
| `recovery_history.json` | Recovery engine | Per-task recovery attempts when a failure was classified |
| `checkpoints/langgraph.sqlite` | LangGraph | Resume source of truth for in-flight execution. `state.json` is the mirror you can open in an editor |

Open `state.json` when you need one file that explains “where is this run.” Open `approvals.json` when you need to prove a human decision. Open `execution_history.json` when you need the timeline.

### Specifications and plans

| Path | Format |
| --- | --- |
| `.agentic/specifications/spec_<id>.json` | Machine spec: title, summary, functional and non-functional requirements, acceptance criteria, assumptions, constraints, in scope, out of scope |
| `.agentic/specifications/spec_<id>.md` | Same content as readable Markdown |
| `.agentic/plans/plan_<id>.json` | Machine plan: summary plus tasks |
| `.agentic/plans/plan_<id>.md` | Same content as readable Markdown |

Each task in the plan JSON has:

| Field | Meaning |
| --- | --- |
| `id`, `name`, `description` | Identity and intent |
| `depends_on` | Task ids that must complete first. The graph is validated; cycles are rejected |
| `status` | `pending`, `ready`, `in_progress`, `completed`, `failed`, `blocked` |
| `agent` | Responsible agent name, often `developer` |
| `acceptance_criteria` | What “done” means for that task |
| `max_retries`, `retry_count` | Retry cap and how many have been used |
| `input_refs`, `output_refs` | Artifact references |
| `error` | Failure text when status is `failed` |
| `recovery_feedback` | Corrective note fed into a later attempt |

### Reports

| Path | Format |
| --- | --- |
| `.agentic/reports/report_<workflow_id>.json` | Full report document: summary, tasks, approvals, events, metrics, test results, design note, stop reason |
| `.agentic/readable/REPORT.md` | Human-readable rendering of that document |

Metrics you should see in the CLI summary and in `metrics.json` include event count, task starts and finishes, task failures, retries (same-operation, corrected, scope reduction), replans, escalations, recovery decisions, commands proposed / approved / rejected / executed, safe stops, and a `completed` flag. If the log cannot support a figure, the field is called out in `insufficient_data` rather than guessed.

### Human-readable copies

`.agentic/readable/` is for reviewers. JSON remains authoritative.

| File | Appears when |
| --- | --- |
| `ANALYSIS.md` | Analysis has been produced. Original requirement, interpretation, assumptions, risks, clarification questions |
| `SPECIFICATION.md` | Spec generated. Latest spec; also copied beside the JSON |
| `PLAN.md` | Plan generated. Tasks plus ASCII and Mermaid graphs |
| `REPORT.md` | After `report` (also written on the release path) |
| `phases/NN_name.md` | Point-in-time snapshot. `NN` is a two-digit index |

Typical phase files:

| File | Contents |
| --- | --- |
| `phases/01_analysis.md` | Analysis snapshot |
| `phases/02_clarification.md` | Essential questions, reasons, and any recorded answers |
| `phases/03_specification.md` | Spec snapshot |
| `phases/04_approval.md` | Specification gate decision, comment, spec id, stop reason |
| `phases/05_plan.md` | Plan snapshot |
| `phases/06_plan_approval.md` | Plan gate decision |
| `phases/07_….md` and higher | Execution cohort summaries (design, implement, test, document). The index starts at 07 and increases by one per summary |

Phase indexes increase as the run proceeds. Later approval decisions get their own phase file; they do not erase `SPECIFICATION.md`. “See also” links inside an approval phase point at the latest analysis, spec, and plan.

### Application files the agents may add

These are **not** under `.agentic/`:

| Provider | Typical writes |
| --- | --- |
| `mock` | `src/generated/<task id>.py` per developer task; `docs/AGENTIC_NOTES.md` from the documentation agent; test commands are proposals such as `python -c "print('test-ok:<task id>')"` |
| `anthropic` | Whatever files the Developer Agent’s structured response validates, still confined to the target root. Documentation still centers on `docs/AGENTIC_NOTES.md` |

A design note produced by the architecture step is stored on the workflow (`design_note` in `state.json`) and included in the report.

### Command evidence

Approved and rejected commands are stored on the workflow as test results (`test_results` in `state.json` and in the report): proposal id, exit code, stdout, stderr, timeout flag, approved flag, task id. Rejected commands have `approved: false` and stderr `Command rejected by human; not executed`.

---

## 9. End-to-end sessions

Run these from the CLI repo root after section 2. They assume the default `mock` provider.

### 9.1 Shortest path (clear requirement, interactive)

```powershell
$t = "..\agentic-manual-e2e"
if (Test-Path $t) { Remove-Item -Recurse -Force $t }
New-Item -ItemType Directory -Path $t | Out-Null

python agenticli_test.py init $t
python agenticli_test.py run $t --interactive --requirement "Add a /health endpoint that returns status ok and the app version string"
```

At each prompt type `a` and press Enter, then Enter again to skip the comment. Expect this order when the requirement is specific enough to skip clarification:

1. Specification approval
2. Plan approval (execution starts by itself)
3. Command approval, possibly more than once
4. Release approval

Then:

```powershell
python agenticli_test.py status $t
python agenticli_test.py report $t
python agenticli_test.py history $t
```

Expect `status: completed`. Open:

- `$t\.agentic\readable\SPECIFICATION.md`
- `$t\.agentic\readable\PLAN.md`
- `$t\.agentic\readable\REPORT.md`
- `$t\.agentic\readable\phases\`
- `$t\.agentic\workflows\workflow_*\state.json`
- `$t\.agentic\workflows\workflow_*\approvals.json`
- `$t\.agentic\workflows\workflow_*\execution_history.json`
- `$t\.agentic\workflows\workflow_*\metrics.json`
- `$t\src\generated\`
- `$t\docs\AGENTIC_NOTES.md`

### 9.2 Same path with explicit gates

Use this when you want to pause and read files between decisions. Substitute the same `$t`.

```powershell
python agenticli_test.py run $t --requirement "Add a /health endpoint that returns status ok and the app version string"
python agenticli_test.py status $t
python agenticli_test.py spec $t
python agenticli_test.py approve $t --comment "spec ok"
# status is now awaiting_plan_approval
python agenticli_test.py plan $t
python agenticli_test.py approve $t --comment "plan ok"
# execution starts and parks on the next gate
python agenticli_test.py status $t
python agenticli_test.py approve $t --comment "run command"
# repeat approve while status is awaiting_command_approval
# when status is awaiting_release_approval:
python agenticli_test.py report $t
python agenticli_test.py approve $t --comment "release"
python agenticli_test.py status $t
```

If you close the terminal while status is `executing` (no pending gate), continue with:

```powershell
python agenticli_test.py resume $t
```

### 9.3 Ambiguous requirement (clarification)

```powershell
python agenticli_test.py init ..\agentic-manual-ambiguous --force
python agenticli_test.py run ..\agentic-manual-ambiguous --requirement "Make sharing better and safer somehow"
python agenticli_test.py status ..\agentic-manual-ambiguous
```

Expect `awaiting_clarification` and a question list. Continue with one `--answer` per question, in printed order, or switch to interactive:

```powershell
python agenticli_test.py run ..\agentic-manual-ambiguous --interactive
```

Recorded answers must show up in `phases/02_clarification.md` and in `state.json` (`clarification_answers`). After answers, the spec gate is the same as section 9.2.

### 9.4 Reject a gate

Plain reject and changes-requested land on different statuses.

At `awaiting_spec_approval`:

```powershell
python agenticli_test.py reject $t --comment "auth model is wrong"
```

Expect `spec_rejected` and `stop_reason: Specification rejected`. The same flag on a plan gate expects `plan_rejected` and `Plan rejected`.

Changes requested:

```powershell
python agenticli_test.py reject $t --changes-requested --comment "Split authentication from storage"
python agenticli_test.py status $t
```

Expect status `stopped` and `stop_reason` `Specification changes requested` or `Plan changes requested`. The approval phase file records `changes_requested`, and `approvals.json` has the same decision. Execution does not start after a plan rejection or a plan changes-request.

To reject a command, wait until `pending_command` is printed, then:

```powershell
python agenticli_test.py reject $t --comment "do not run"
```

The command does not run. The task is marked failed with `Command rejected by human`, history gets a `command_rejected` event, and stored evidence has `approved: false`. `--changes-requested` on a command or destructive gate is stored as a reject. Recovery may then retry, replan, or safe-stop under the budgets in section 4; the workflow does not become `completed`.

Rejecting release (or passing `--changes-requested` at the release gate) sets `safe_stopped` with `stop_reason: Release rejected`.

### 9.5 Phase 6 demo target (brownfield)

The durable FastAPI seed is `..\abassign1`. Full scripts for greenfield, brownfield, and ambiguous runs, plus the independence check, are in [docs/phase6/DEMO.md](docs/phase6/DEMO.md). Summary:

```powershell
# Optional clean workflow state. Does not delete the FastAPI app.
Remove-Item -Recurse -Force ..\abassign1\.agentic -ErrorAction SilentlyContinue
python agenticli_test.py init ..\abassign1
python agenticli_test.py run ..\abassign1 --interactive --requirement "Improve sharing security: private shares must not appear in GET /shares for anonymous callers; GET /shares/{token} for non-public shares must require an owner query parameter matching the share owner; keep public shares readable without auth."
```

Independence, from the target (its own venv, not the CLI venv):

```powershell
cd ..\abassign1
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

From the CLI repo, `Test-Path .\abassign1` must be `False`.

### 9.6 Prove isolation

```powershell
python agenticli_test.py init .
```

Expect a red isolation error and exit code 3. No `.agentic/` directory should appear in the CLI repo from this command.

```powershell
python agenticli_test.py init ..\nonempty-demo
```

If that directory already has files and no `.agentic/`, expect exit code 2 until you pass `--force`.

---

## 10. Agents and what they do

Orchestration is a LangGraph workflow. You do not invoke agents by name. They run when execution is in progress.

| Agent | Role |
| --- | --- |
| Requirement analyzer | Interprets the requirement, lists assumptions and risks, emits essential clarification questions |
| Specification generator | Turns the understanding into the spec model |
| Task planner | Decomposes the approved spec into tasks and `depends_on` edges |
| Architecture agent | Writes a design note used by later agents |
| Developer agent | Proposes file writes. Mock: `src/generated/<task id>.py`. Live: structured JSON validated before any write. Oversized output is batched |
| Testing agent | Proposes a command. It never executes it. Mock proposes `python -c "print('test-ok:<task id>')"` |
| Failure analysis / recovery | Classifies a failure and chooses a bounded strategy |
| Documentation agent | Writes `docs/AGENTIC_NOTES.md` in the target |

Developer writes go through the workspace path checks. Testing and any other shell go through command approval.

### Recovery (automatic, then human)

On a task failure the engine classifies evidence into a category such as `transient_provider`, `rate_limit`, `invalid_structured_output`, `output_truncated`, `schema_validation`, `implementation_error`, `test_failure`, `dependency_failure`, `workspace_violation`, `invalid_file_operation`, `permission_failure`, or `unknown`.

It then picks one strategy, within the budgets in section 4:

| Strategy | Effect |
| --- | --- |
| `retry_same` | Run the same operation again |
| `retry_corrected` | Run again with corrective feedback |
| `reduce_scope` | Shrink what the task attempts |
| `replan` | Patch the plan and return to **plan approval**. A replan is not applied silently |
| `escalate` | Stop safely (`safe_stopped`) and surface `stop_reason` |

Attempts are appended to `recovery_history.json` and mirrored as audit events. When budgets are spent, the workflow safe-stops instead of looping. `report` counts these events; it does not estimate a success rate when the log has no recovery records (`insufficient_data`).

---

## 11. Repository map (the CLI itself)

```text
CharlesSchwabAssignment-abak/
├── pyproject.toml              # package agentic-engineer, script name agentic
├── agenticli_test.py           # local launcher
├── agentic.config.example.toml # committed config template
├── .env.example
├── requirement.md              # sample multiline requirement for --requirement-file
├── USER_MANUAL.md              # this manual
├── TEST_CHECKLIST.md
├── README.md
├── REQUIREMENTS.md
├── ARCHITECTURE.md
├── ARCHITECTURE_DECISIONS.md
├── IMPLEMENTATION_PLAN.md
├── AGENTS.md                   # rules for coding agents editing this repo
├── docs/phase2/ … docs/phase6/
├── src/agentic_engineer/
│   ├── cli/                    # Typer commands and interactive prompts
│   ├── config/                 # settings, TOML discovery
│   ├── models/                 # Pydantic records (workflow, spec, plan, approval, recovery)
│   ├── workspace/              # target root, isolation, .agentic layout
│   ├── persistence/            # JSON stores and readable Markdown
│   ├── llm/                    # mock + Anthropic
│   ├── graph/                  # LangGraph requirement + execution workflows
│   ├── agents/                 # analyzer, spec, planner, architecture, developer, testing, docs
│   ├── governance/             # approval records
│   ├── execution/              # command runner, recovery, audit events
│   ├── reporting/              # report builder
│   └── audit/                  # metrics from events
└── tests/{unit,integration}/
```

Phase documents under `docs/` are the delivery record (specs, plans, the Phase 6 runbook). For an assessment of **behavior**, prefer this manual, `TEST_CHECKLIST.md`, and a live `status` / `.agentic` tree over the phase plans.

Logging uses the standard library at `AGENTIC_LOG_LEVEL`. `--verbose` is the switch to use when a run fails and the status line is not enough. Logs go to the terminal; they are not a substitute for `execution_history.json`.

---

## 12. Assessment checklist

Work top to bottom. Check the box only after you have seen the artifact, not only the command’s exit code.

1. Python 3.11+, venv, `pip install -e ".[dev]"`, `pytest` green.
2. `version` prints `0.1.0`.
3. `init` on this repo fails with exit code 3.
4. `init` on a new sibling directory creates `.agentic/config.json` with null active ids.
5. `status` on that directory reports `phase: initialized (no active workflow)`.
6. A clear requirement reaches `awaiting_spec_approval` with `SPECIFICATION.md` and `spec_*.json`.
7. Approving the spec reaches `awaiting_plan_approval` with a dependency graph (`plan` command) and `plan_*.json`.
8. Approving the plan starts execution and parks on `awaiting_command_approval` with `pending_command` filled in **before** any test process runs.
9. Approving the command records evidence (exit code and output) in workflow state / the report.
10. `awaiting_release_approval` then `approve` yields `completed`.
11. `report` writes `REPORT.md`, `reports/report_*.json`, and `metrics.json`. Counts match `history`.
12. `approvals.json` shows specification, plan, command, and release decisions with `decision` set by you, each with `decided_at`.
13. An ambiguous requirement parks at `awaiting_clarification`, and your answers appear in `02_clarification.md`.
14. A reject path records `rejected` or `changes_requested` and does not mark the workflow `completed`.
15. `revert` exits 1 and does not delete target files.
16. Optional: repeat one run with Anthropic configured and confirm the target still has no CLI dependency.
17. Optional: Phase 6 brownfield on `../abassign1` using [docs/phase6/DEMO.md](docs/phase6/DEMO.md).

---

## 13. Troubleshooting

| What you see | What it means | What to do |
| --- | --- | --- |
| `Target is not initialized (missing .agentic/)` | `init` was not run on that path | `agentic init <path>` (add `--force` if the directory already has files) |
| Exit code 2, “not empty” | Brownfield init needs confirmation | `init <path> --force` |
| Exit code 3, “Refusing to use CLI repository” | The path is this repo or inside it | Point at a sibling directory |
| `Pass either --requirement or --requirement-file, not both` | Both requirement sources were set | Use one |
| `Pass either a requirement … or --answer, not both` | New requirement mixed with clarification answers | Start with the requirement; call `run --answer` only after `awaiting_clarification` |
| `Pass either --answer or --interactive, not both` | Interactive wants to prompt for answers itself | Drop `--answer` or drop `-i` |
| `Human gate pending` | `run` without `-i` hit a gate | `approve`, `reject`, or `run -i` |
| `No specification generated yet` | `spec` before the spec exists | `status`; finish clarification first |
| `Requirement file not found` or `is empty` | Bad `-R` path or blank file | Fix the path; file is read as UTF-8 |
| Status stuck at `spec_approved` | Plan generation did not complete | `plan <path> --generate` or `run -i` |
| Status `safe_stopped` with a red failure summary | Recovery escalated | Read `stop_reason`, the failed task’s `error`, `recovery_history.json`, and `history`. Start a new requirement if you want a clean run; delete `.agentic` first if the active pointer should reset |
| `approve` says nothing is pending | Status is not a gate | `status` and follow the hint line it prints |
| Command seems to do nothing useful | Default mock test command only prints `test-ok:<task id>` | Expected offline. Configure Anthropic for real test proposals |
| Anthropic errors immediately | Missing package or key | `pip install -e ".[dev,anthropic]"` and set `api_key` in `agentic.toml` or `ANTHROPIC_API_KEY`. `--verbose` shows the provider error |
| `report` metrics look sparse | Early in the workflow, or mock run with few events | `insufficient_data` lists gaps. Run `history` to see the raw events |
| Want a clean target workflow | Old `.agentic` is still active | `Remove-Item -Recurse -Force <path>\.agentic`, then `init` again. Application source outside `.agentic` remains |
| Resume does not move a gate | Resume does not approve | `approve` or `run -i` |

---

## 14. Limits of this version

- Version 0.1.0. One active workflow pointer per target.
- Providers are `mock` and `anthropic` only.
- No web UI. Gates are terminal prompts or `approve` / `reject`.
- No file-level revert and no git hard reset. Checkpoint resume is the recovery path for an interrupted graph.
- Destructive proposals are gated and recorded. Approval in the current slice records the decision; it is not a general-purpose delete tool.
- Parallelism is limited to a cohort of tasks that do not depend on each other, then a sync barrier.
- Replan returns to human plan approval. The model cannot approve the new plan.
- Git commit hooks, multi-provider failover, and a hosted dashboard are outside this prototype.

When you write up the assessment, separate those limits from defects: a mock stub under `src/generated/` is the offline contract; a missing approval record for a command that ran would be a defect.
