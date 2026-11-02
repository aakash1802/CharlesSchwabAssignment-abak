# Requirements

Assignment brief for a working prototype. Statements below are the brief. Items the brief does not decide stay in Open questions.

## Status

Captured. Acceptance criteria cover the path from a requirement to a reviewable outcome. Language, artifact format, and the control mechanism for autonomy are still open.

## Problem statement

Build a working prototype that transforms a requirement into a reviewable engineering outcome using an agentic execution model. Demonstrate requirement understanding, task decomposition, multi-step execution, and output generation and validation. Focus on end-to-end software development lifecycle (SDLC) automation with controlled autonomy.

## Source statements

| Id | Statement |
| --- | --- |
| R1 | Build a working prototype. |
| R2 | The prototype transforms a requirement into a reviewable engineering outcome. |
| R3 | The prototype uses an agentic execution model. |
| R4 | The prototype demonstrates requirement understanding. |
| R5 | The prototype demonstrates task decomposition. |
| R6 | The prototype demonstrates multi-step execution. |
| R7 | The prototype demonstrates output generation and validation. |
| R8 | The focus is end-to-end SDLC automation with controlled autonomy. |

## Users and context

| Question | Answer |
| --- | --- |
| Who uses the result? | A reviewer of the engineering outcome (R2). The brief does not name a role or team. |
| What job does it do? | Transform a requirement into a reviewable engineering outcome through an agentic execution model (R2, R3). |
| What inputs does it receive? | A requirement (R2). The format is not specified. |
| What outputs must it produce? | A reviewable engineering outcome that shows requirement understanding, the task breakdown, the execution steps, the generated output, and the validation result (R2, R4, R5, R6, R7). |

## In scope

- A working prototype (R1).
- An agentic execution model that takes a requirement through to an outcome (R2, R3).
- Requirement understanding (R4).
- Task decomposition (R5).
- Multi-step execution (R6).
- Output generation and validation (R7).
- End-to-end SDLC automation with controlled autonomy (R8).

## Out of scope

- Production operation beyond a working prototype (R1).
- Autonomy with no reviewer-visible bound (R2, R8).
- Behaviors the brief does not request. See Open questions before treating anything else as scope.

## Constraints

| Constraint | Detail |
| --- | --- |
| Language / platform | Not stated. A local Python virtual environment exists; it is not a requirement. |
| External services | Not stated. |
| Time or size limits | Not stated. |
| Data handling | Not stated. Repository rule: credentials and personal data stay out of the repository. |

## Acceptance criteria

- [ ] AC1. Given a requirement, when the prototype runs, then it produces an engineering outcome a reviewer can inspect (R1, R2).
- [ ] AC2. Given a requirement, when the prototype runs, then the outcome shows how that requirement was understood (R4).
- [ ] AC3. Given a requirement, when the prototype runs, then the outcome shows a decomposition into tasks (R5).
- [ ] AC4. Given a requirement, when the prototype runs, then execution has more than one step and those steps are visible in the outcome (R6).
- [ ] AC5. Given a requirement, when the prototype runs, then it generates an output and records a validation result for that output (R7).
- [ ] AC6. Given one requirement, when the prototype runs to completion, then a reviewer can follow one path from that requirement through understanding, task decomposition, multi-step execution, generated output, and validation (R3, R8).

R8 also requires controlled autonomy. How control is applied is an open question, so there is no separate pass/fail check for the control mechanism yet.

## Assumptions

- The input is a single requirement (R2).
- "Working" means the prototype can be run on a requirement and produce the outcome (R1).
- "Reviewable" means a person can inspect the outcome and the path that produced it (R2).
- "Multi-step" means more than one execution step (R6).
- Understanding, decomposition, execution, generation, and validation are stages of one flow (R8).

## Open questions

- [ ] What form is the input requirement (plain text, a file, a ticket, or something else)?
- [ ] Which artifacts count as a reviewable engineering outcome (document, code, tests, execution trace, or a combination)?
- [ ] What does controlled autonomy mean here (human approval, policy limits, a step budget, or another bound)?
- [ ] Which SDLC activities sit inside "end-to-end" beyond understanding, decomposition, execution, generation, and validation?
- [ ] Which language, framework, and libraries should the prototype use?
- [ ] Does the assignment require a Charles Schwab API, sandbox, or sample data? The brief does not mention one.
- [ ] What must be submitted besides the running prototype?
