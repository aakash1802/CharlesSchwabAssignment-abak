# Agent guide

Working agreement for coding agents in this repository. Read this file before changing the project.

## Current phase

Requirements are captured in [REQUIREMENTS.md](REQUIREMENTS.md). [ARCHITECTURE.md](ARCHITECTURE.md) records the agentic stage sequence: understand, decompose, execute in multiple steps, generate, and validate. There is no application code, test suite, or chosen stack yet. A local Python virtual environment (`.venv`) is present and is not a design decision.

Do not add application code, dependencies, or project config until [ARCHITECTURE.md](ARCHITECTURE.md) records the language, framework, source layout, and how to run and verify the prototype. Leave open questions in [REQUIREMENTS.md](REQUIREMENTS.md) unanswered until a decision is actually made.

## Read first

1. [README.md](README.md) for status and layout.
2. [REQUIREMENTS.md](REQUIREMENTS.md) for scope and acceptance criteria.
3. [ARCHITECTURE.md](ARCHITECTURE.md) for components and open decisions.

If a task conflicts with those documents, stop and ask. Do not invent requirements to fill the gap.

## How to work

- Keep changes small and limited to the requested task.
- Update the matching document when behavior, scope, or structure changes.
- Leave placeholder sections marked `TBD` until a decision is actually made.
- Do not commit secrets, tokens, or local environment files.
- Do not treat `.venv` as source. Do not edit files inside it.

## When implementation starts

Fill these in before writing features:

- Language, framework, and dependency set
- Source and test layout
- How to run and verify the project
- External systems, including any Charles Schwab APIs, and how credentials are supplied

Prefer the simplest design that meets the written acceptance criteria.
