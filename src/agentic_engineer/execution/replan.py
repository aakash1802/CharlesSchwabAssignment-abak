"""Simplified material plan patch + downstream invalidation (Phase 5)."""

from __future__ import annotations

from typing import Any

from agentic_engineer.models.common import utc_now
from agentic_engineer.models.task import Task


def apply_material_plan_patch(
    tasks: list[Task],
    *,
    failed_task_id: str,
    note: str = "",
) -> tuple[list[Task], dict[str, Any]]:
    """Reset the failed task and invalidate transitive dependents to pending.

    Does not raise max_task_retries. Returns updated tasks and a patch summary.
    """
    by_id = {t.id: t for t in tasks}
    if failed_task_id not in by_id:
        return tasks, {"applied": False, "reason": "unknown failed_task_id"}

    # Transitive dependents: tasks that (indirectly) depend on failed_task_id.
    dependents: set[str] = set()
    changed = True
    while changed:
        changed = False
        for task in tasks:
            if task.id in dependents or task.id == failed_task_id:
                continue
            if any(dep == failed_task_id or dep in dependents for dep in task.depends_on):
                dependents.add(task.id)
                changed = True

    invalidated = sorted(dependents | {failed_task_id})
    updated: list[Task] = []
    for task in tasks:
        if task.id not in invalidated:
            updated.append(task)
            continue
        updated.append(
            task.model_copy(
                update={
                    "status": "pending",
                    "error": None,
                    "updated_at": utc_now(),
                    "description": (
                        f"{task.description}\n\n[replan] {note}".strip()
                        if note
                        else task.description
                    ),
                }
            )
        )

    summary = {
        "applied": True,
        "failed_task_id": failed_task_id,
        "invalidated_task_ids": invalidated,
        "note": note,
        "material": True,
    }
    return updated, summary
