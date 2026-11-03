"""Architecture / Design agent — deterministic inspect + optional LLM design note."""

from __future__ import annotations

from pathlib import Path

from agentic_engineer.llm.base import LLMProvider, LLMRequest
from agentic_engineer.llm.mock import MockProvider
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.workspace.workspace import Workspace


def inspect_workspace(workspace: Workspace) -> dict[str, object]:
    """Deterministic brownfield/greenfield inspect (no LLM)."""
    root = workspace.root
    entries = sorted(p.name for p in root.iterdir() if p.name != ".agentic")
    py_files = sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*.py")
        if ".agentic" not in p.parts
    )
    return {
        "root": str(root),
        "top_level": entries,
        "python_files": py_files[:50],
        "is_greenfield": len(entries) == 0,
    }


def _deterministic_note(plan: EngineeringPlan, inspect: dict[str, object]) -> str:
    kind = "greenfield" if inspect.get("is_greenfield") else "brownfield"
    top = ", ".join(map(str, inspect.get("top_level") or [])) or "(empty)"
    return "\n".join(
        [
            f"Design note ({kind}) for plan {plan.id}",
            f"Summary: {plan.summary}",
            f"Top-level entries: {top}",
            "Approach: apply scoped Workspace edits per task; "
            "gate all shell via CommandRunner.",
        ]
    )


class ArchitectureAgent:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def design_note(
        self,
        *,
        workspace: Workspace,
        plan: EngineeringPlan,
        inspect: dict[str, object],
    ) -> str:
        # Phase 4 default: deterministic note. LLM only when mock has scripted responses.
        if isinstance(self._provider, MockProvider) and self._provider.has_queued_responses:
            response = self._provider.complete(
                LLMRequest(
                    prompt=(
                        f"Plan summary: {plan.summary}\nInspect: {inspect}\n"
                        "Write a short design note (plain text)."
                    ),
                    system="You are an architecture agent.",
                )
            )
            note = response.text.strip()
        else:
            note = _deterministic_note(plan, inspect)

        rel = Path(".agentic") / "artifacts" / "design_note.md"
        workspace.write_text(rel, f"# Design note\n\n{note}\n")
        return note
