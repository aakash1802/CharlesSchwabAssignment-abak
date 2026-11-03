"""Reduce task scope by splitting into smaller dependent subtasks."""

from __future__ import annotations

from typing import Any

from agentic_engineer.graph.dependency import validate_graph
from agentic_engineer.models.common import utc_now
from agentic_engineer.models.task import Task


_SCOPE_MARKER = "_s"


def _next_task_id(existing: set[str], base: str, index: int) -> str:
    candidate = f"{base}{_SCOPE_MARKER}{index}"
    n = index
    while candidate in existing:
        n += 1
        candidate = f"{base}{_SCOPE_MARKER}{n}"
    return candidate


def lineage_task_ids(task_id: str) -> list[str]:
    """Ancestor chain for scope-reduced ids (`t7`, `t7_s1`, `t7_s1_s1`, …).

    Budgets must count reduce_scope attempts across this chain; otherwise each
    new subtask resets `(1/2)` and nesting never escalates.
    """
    if _SCOPE_MARKER not in task_id:
        return [task_id]
    parts = task_id.split(_SCOPE_MARKER)
    chain = [parts[0]]
    for i in range(1, len(parts)):
        chain.append(_SCOPE_MARKER.join(parts[: i + 1]))
    return chain


def lineage_depth(task_id: str) -> int:
    """Number of `_sN` suffixes on a task id (0 for a root task)."""
    return max(0, len(lineage_task_ids(task_id)) - 1)


def default_scope_parts(task: Task) -> list[tuple[str, str]]:
    """Logical subtask boundaries preserving acceptance criteria."""
    criteria = list(task.acceptance_criteria) or [
        "Satisfy the parent task acceptance criteria."
    ]
    mid = max(1, len(criteria) // 2)
    part_a = criteria[:mid]
    part_b = criteria[mid:] or criteria[-1:]
    size_hint = (
        "Keep generated file contents short enough to fit in one structured "
        "JSON response (prefer a concise README or a single small file)."
    )
    return [
        (
            f"{task.name} (core)",
            (
                f"Reduced-scope core for `{task.id}`: {task.description}\n\n"
                "Focus on the primary deliverable only; defer remaining files.\n"
                f"{size_hint}\n"
                "Acceptance:\n- " + "\n- ".join(part_a)
            ),
        ),
        (
            f"{task.name} (remainder)",
            (
                f"Complete remaining work for `{task.id}` after core lands.\n"
                f"Original: {task.description}\n"
                f"{size_hint}\n"
                "Acceptance:\n- " + "\n- ".join(part_b)
            ),
        ),
    ]


def apply_scope_reduction(
    tasks: list[Task],
    *,
    failed_task_id: str,
    note: str = "",
    parts: list[tuple[str, str]] | None = None,
) -> tuple[list[Task], dict[str, Any]]:
    """Replace a failed task with smaller chained subtasks.

    Preserves unaffected completed tasks. Downstream dependents of the failed
    task are rewired to depend on the final subtask. Validates the new graph.
    """
    by_id = {t.id: t for t in tasks}
    if failed_task_id not in by_id:
        return tasks, {"applied": False, "reason": "unknown failed_task_id"}

    original = by_id[failed_task_id]
    segments = parts or default_scope_parts(original)
    if len(segments) < 2:
        segments = default_scope_parts(original)

    existing_ids = set(by_id)
    subtasks: list[Task] = []
    prev_id: str | None = None
    created_ids: list[str] = []
    for index, (name, description) in enumerate(segments, start=1):
        new_id = _next_task_id(existing_ids, failed_task_id, index)
        existing_ids.add(new_id)
        created_ids.append(new_id)
        depends = list(original.depends_on) if prev_id is None else [prev_id]
        subtasks.append(
            Task(
                id=new_id,
                name=name,
                description=(
                    f"{description}\n\n[scope_reduce] {note}".strip()
                    if note
                    else description
                ),
                depends_on=depends,
                status="pending",
                agent=original.agent,
                acceptance_criteria=list(original.acceptance_criteria),
                max_retries=original.max_retries,
                retry_count=0,
                input_refs=list(original.input_refs),
                output_refs=list(original.output_refs),
            )
        )
        prev_id = new_id

    final_id = created_ids[-1]
    updated: list[Task] = []
    for task in tasks:
        if task.id == failed_task_id:
            # Drop the oversized parent; subtasks inherit its work and deps.
            continue
        if failed_task_id in task.depends_on:
            new_deps = [
                final_id if dep == failed_task_id else dep for dep in task.depends_on
            ]
            # Also drop the failed id if it somehow remains.
            new_deps = [d for d in new_deps if d != failed_task_id]
            updated.append(
                task.model_copy(
                    update={"depends_on": new_deps, "updated_at": utc_now()}
                )
            )
        else:
            updated.append(task)

    updated.extend(subtasks)
    validation = validate_graph(updated)
    summary: dict[str, Any] = {
        "applied": validation.ok,
        "failed_task_id": failed_task_id,
        "created_task_ids": created_ids,
        "final_task_id": final_id,
        "note": note,
        "validation_ok": validation.ok,
        "validation_errors": validation.error_messages,
    }
    if not validation.ok:
        return tasks, summary
    return updated, summary
