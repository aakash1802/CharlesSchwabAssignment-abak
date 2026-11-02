"""Deterministic task-dependency graph validation and scheduling helpers (Phase 3).

The task graph is data. This module validates it and computes ready sets;
LangGraph (Phase 4) executes according to these results — no second DAG runner.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from agentic_engineer.models.task import Task


@dataclass(frozen=True)
class GraphValidationError:
    code: str
    message: str
    task_id: str | None = None


@dataclass(frozen=True)
class GraphValidationResult:
    ok: bool
    errors: list[GraphValidationError]

    @property
    def error_messages(self) -> list[str]:
        return [e.message for e in self.errors]


def validate_graph(tasks: list[Task]) -> GraphValidationResult:
    """Validate ids, dependency references, self-deps, and cycles."""
    errors: list[GraphValidationError] = []
    if not tasks:
        errors.append(
            GraphValidationError(
                code="empty_graph",
                message="Plan must contain at least one task",
            )
        )
        return GraphValidationResult(ok=False, errors=errors)

    ids = [t.id for t in tasks]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for task_id in ids:
        if task_id in seen:
            duplicates.add(task_id)
        seen.add(task_id)
    for task_id in sorted(duplicates):
        errors.append(
            GraphValidationError(
                code="duplicate_id",
                message=f"Duplicate task id: {task_id}",
                task_id=task_id,
            )
        )

    id_set = set(ids)
    by_id = {t.id: t for t in tasks}

    for task in tasks:
        for dep in task.depends_on:
            if dep == task.id:
                errors.append(
                    GraphValidationError(
                        code="self_dependency",
                        message=f"Task {task.id} depends on itself",
                        task_id=task.id,
                    )
                )
            elif dep not in id_set:
                errors.append(
                    GraphValidationError(
                        code="unknown_dependency",
                        message=f"Task {task.id} depends on unknown id: {dep}",
                        task_id=task.id,
                    )
                )

    # Cycle detection via Kahn's algorithm on the known-id subgraph.
    if not duplicates:
        indegree: dict[str, int] = {tid: 0 for tid in id_set}
        adjacency: dict[str, list[str]] = defaultdict(list)
        for task in tasks:
            for dep in task.depends_on:
                if dep not in id_set or dep == task.id:
                    continue
                adjacency[dep].append(task.id)
                indegree[task.id] += 1

        queue: deque[str] = deque(
            sorted(tid for tid, deg in indegree.items() if deg == 0)
        )
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for child in sorted(adjacency[node]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

        if visited != len(id_set):
            cyclic = sorted(tid for tid, deg in indegree.items() if deg > 0)
            errors.append(
                GraphValidationError(
                    code="cycle",
                    message=f"Dependency cycle involving: {', '.join(cyclic)}",
                    task_id=cyclic[0] if cyclic else None,
                )
            )

    # Orphan warning-as-error policy: every non-root should be reachable from roots.
    # Soft: only when graph otherwise structurally valid on ids.
    if not errors:
        roots = [t.id for t in tasks if not t.depends_on]
        if not roots and tasks:
            errors.append(
                GraphValidationError(
                    code="no_roots",
                    message="Graph has no root tasks (every task has dependencies)",
                )
            )
        else:
            reachable: set[str] = set()
            children: dict[str, list[str]] = defaultdict(list)
            for task in tasks:
                for dep in task.depends_on:
                    children[dep].append(task.id)
            stack = list(roots)
            while stack:
                node = stack.pop()
                if node in reachable:
                    continue
                reachable.add(node)
                stack.extend(children.get(node, []))
            orphans = sorted(id_set - reachable)
            for orphan in orphans:
                errors.append(
                    GraphValidationError(
                        code="orphan",
                        message=(
                            f"Task {orphan} is unreachable from roots "
                            f"(name={by_id[orphan].name})"
                        ),
                        task_id=orphan,
                    )
                )

    return GraphValidationResult(ok=not errors, errors=errors)


def ready_tasks(
    tasks: list[Task],
    *,
    completed_ids: set[str] | None = None,
) -> list[Task]:
    """Return tasks whose dependencies are all completed (or have none)."""
    completed = completed_ids if completed_ids is not None else {
        t.id for t in tasks if t.status == "completed"
    }
    ready: list[Task] = []
    for task in tasks:
        if task.id in completed:
            continue
        if task.status in ("completed", "in_progress", "failed"):
            continue
        if all(dep in completed for dep in task.depends_on):
            ready.append(task)
    return ready


def parallel_cohorts(
    tasks: list[Task],
    *,
    completed_ids: set[str] | None = None,
) -> list[list[Task]]:
    """Partition remaining work into successive parallel-ready cohorts.

    Cohort 0 is the current ready set. Each later cohort assumes prior cohorts
    completed (simulation for planning display — not execution).
    """
    remaining = {t.id: t for t in tasks}
    completed = set(completed_ids or set())
    # Also treat already-completed statuses as done.
    for task in tasks:
        if task.status == "completed":
            completed.add(task.id)

    cohorts: list[list[Task]] = []
    while True:
        ready = [
            remaining[tid]
            for tid in sorted(remaining)
            if tid not in completed
            and all(dep in completed for dep in remaining[tid].depends_on)
        ]
        if not ready:
            break
        cohorts.append(ready)
        for task in ready:
            completed.add(task.id)
            remaining.pop(task.id, None)
        if not remaining:
            break
        # Detect stuck remainder (should not happen after validate_graph).
        if not ready:
            break
    return cohorts


def render_mermaid(tasks: list[Task]) -> str:
    """Render a simple Mermaid flowchart of task dependencies."""
    lines = ["flowchart TD"]
    for task in tasks:
        label = task.name.replace('"', "'")
        lines.append(f'  {task.id}["{task.id}: {label}"]')
    for task in tasks:
        for dep in task.depends_on:
            lines.append(f"  {dep} --> {task.id}")
    return "\n".join(lines)


def render_ascii(tasks: list[Task]) -> str:
    """Render a compact ASCII dependency listing."""
    lines: list[str] = []
    for task in tasks:
        deps = ", ".join(task.depends_on) if task.depends_on else "(none)"
        lines.append(f"{task.id}: {task.name}")
        lines.append(f"  depends_on: {deps}")
        lines.append(f"  agent: {task.agent}  status: {task.status}")
    return "\n".join(lines)
