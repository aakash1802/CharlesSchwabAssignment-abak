---
name: requirement-to-spec
description: >-
  Turns a requirements brief into a normative SPEC.md. Use when the user asks
  to convert requirements into a spec, write a specification from
  REQUIREMENTS.md or an assignment brief, or run requirement-to-spec.
---

# Requirement to spec

Read the requirements and write `SPEC.md` at the repository root. Do not write application code.

## Sources

Use only these, in order:

1. The requirements text in the current user message.
2. `REQUIREMENTS.md` when it contains a real brief.

Ignore `TBD` placeholders. Do not take scope from `ARCHITECTURE.md` or `README.md`.

If both sources exist and they disagree, the current user message wins. Record the disagreement under Open questions.

## Stop when there is no brief

If the problem statement is missing or still `TBD`, do not write `SPEC.md`. Reply with the missing items:

- problem statement
- inputs and outputs
- in-scope behavior
- constraints that change the design
- how a correct result is judged

## Rules

- Every normative statement is either traced to a requirement id or labeled **Assumption**.
- Do not invent users, APIs, data fields, success behavior, or acceptance criteria.
- Unknowns go under Open questions. They are not requirements.
- Normative words are `must` and `must not`. Use `may` only for optional behavior that a requirement allows.
- Each acceptance criterion is testable without looking at implementation details.
- Leave `ARCHITECTURE.md` unchanged.

Number source statements `R1`, `R2`, … when the brief has no ids. Cite them inline as `(R1)`.

## Steps

1. Read the sources above.
2. List requirement ids and separate facts from gaps.
3. Draft `SPEC.md` from the template below.
4. Check the draft:
   - each `must` cites a requirement id or is an **Assumption**
   - no acceptance criterion depends on an open question
   - out of scope includes behavior the brief excludes
   - the file contains no code
5. Write `SPEC.md`.
6. In the reply, list assumptions and open questions. Do not restate the whole spec.

## Template

```markdown
# Spec

Status: Draft

## Purpose

[One paragraph. What the solution must accomplish and for whom.]

## Sources

| Id | Requirement |
| --- | --- |
| R1 | [Short source statement] |

## In scope

- [Behavior the solution must provide] (R1)

## Out of scope

- [Behavior the solution must not provide, or that the brief leaves out]

## Behavior

1. Given [input or state], the solution must [observable result] (R1).

## Data

| Item | Direction | Description | Source |
| --- | --- | --- | --- |
| [name] | input / output | [what it contains] | R1 |

## Constraints

- The solution must [constraint] (R1).

## Acceptance criteria

- [ ] AC1. Given [fixture or condition], when [action], then [observable result] (R1).

## Assumptions

- [Only items not stated in the brief, each labeled as an assumption.]

## Open questions

- [ ] [Unknown that blocks or changes a requirement. No invented answer.]
```

## Additional resources

For a worked example of traced statements versus invented scope, see [examples.md](examples.md).
