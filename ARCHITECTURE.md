# Architecture

Execution shape for the prototype in [REQUIREMENTS.md](REQUIREMENTS.md). The pipeline below is decided by that brief. Language, storage, entry point, and the autonomy control mechanism are not decided.

## Status

Draft. The stage sequence is recorded. No components are implemented.

## Context

| Topic | Notes |
| --- | --- |
| Problem | Transform a requirement into a reviewable engineering outcome (R2). |
| Users | A reviewer of that outcome (R2). |
| In scope | Agentic, multi-step SDLC automation under controlled autonomy (R3, R6, R8). |
| Out of scope | Production operation, and autonomy with no reviewer-visible bound (R1, R8). |

## Goals

- Meet the acceptance criteria in [REQUIREMENTS.md](REQUIREMENTS.md).
- Make requirement understanding, task decomposition, execution steps, generated output, and validation visible to a reviewer (R4, R5, R6, R7).
- Keep autonomy controlled so a reviewer can see the bound on execution (R8). The mechanism is still an open question.
- Keep the design small enough to explain and review.

## Non-goals

- A production SDLC platform (R1).
- External integrations the brief does not name.
- A stack choice. A local Python virtual environment exists and is not a decision.

## System sketch

One requirement moves through the stages below. Each stage leaves a reviewable record. Later stages consume the records from earlier stages.

```text
[Requirement]
      |
      v
[Understand] ---- recorded understanding
      |
      v
[Decompose] ----- task breakdown
      |
      v
[Execute steps] - step records, inside a controlled-autonomy bound
      |
      v
[Generate] ------ engineering output
      |
      v
[Validate] ------ validation result
      |
      v
[Reviewable outcome: path + output + validation]
```

## Components

| Component | Responsibility | Status |
| --- | --- | --- |
| Requirement intake | Accept one requirement (R2) | Planned. Format TBD |
| Understanding | Produce a recorded reading of the requirement (R4) | Planned |
| Decomposition | Break that reading into tasks (R5) | Planned |
| Execution | Carry out the tasks in more than one step under an agentic model (R3, R6) | Planned. Control mechanism TBD |
| Generation | Produce the engineering output (R7) | Planned. Artifact type TBD |
| Validation | Check the generated output and record the result (R7) | Planned. Checks TBD |
| Review assembly | Present the path, output, and validation as one outcome (R2, R8) | Planned |
| Integrations | External systems | None selected |
| Persistence | Where stage records and the outcome are stored | TBD |
| Tests | Automated checks against the acceptance criteria | TBD |

## Data

| Item | Notes |
| --- | --- |
| Inputs | One requirement (R2). Schema TBD. |
| Outputs | Recorded understanding, task breakdown, execution-step records, generated output, validation result, assembled into one reviewable outcome (R2, R4, R5, R6, R7). |
| Stored data | TBD. The outcome must remain available for review; the store is not chosen. |
| Sensitive data | The brief does not describe sensitive data. Credentials stay out of the repository. |

## External systems

No integrations are selected.

The brief does not name an API, model provider, or data source. If one is required later, record it here with:

- Which system
- Authentication method
- What is mocked in tests versus called for real
- Failure behavior that changes the outcome

## Quality attributes

| Attribute | Target |
| --- | --- |
| Correctness | Acceptance criteria AC1–AC6 in [REQUIREMENTS.md](REQUIREMENTS.md) |
| Reviewability | A reviewer can follow the path from requirement to validation result (R2, R8) |
| Controlled autonomy | Execution stays inside a bound the reviewer can inspect (R8). Mechanism TBD |
| Testability | Core stage logic can be checked against AC1–AC6 without undecided external systems |
| Security | No secrets in source control |

## Open decisions

- [ ] Input format and the artifacts that count as the engineering outcome
- [ ] How controlled autonomy is enforced (R8)
- [ ] Language and libraries (a Python virtual environment exists; the stack is not chosen)
- [ ] Process shape: script, service, library, or something else
- [ ] Persistence, if any
- [ ] Whether any external system, including a Charles Schwab API, is in scope
- [ ] How the prototype is run and demonstrated
