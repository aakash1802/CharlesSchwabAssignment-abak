"""Unit tests for deterministic dependency graph validation (Phase 3)."""

from __future__ import annotations

from agentic_engineer.graph.dependency import (
    parallel_cohorts,
    ready_tasks,
    render_mermaid,
    validate_graph,
)
from agentic_engineer.models.task import Task


def _task(task_id: str, *deps: str, name: str | None = None) -> Task:
    return Task(
        id=task_id,
        name=name or task_id,
        depends_on=list(deps),
    )


def test_validate_empty_graph() -> None:
    result = validate_graph([])
    assert not result.ok
    assert any(e.code == "empty_graph" for e in result.errors)


def test_validate_unknown_dependency() -> None:
    result = validate_graph([_task("t1", "missing")])
    assert not result.ok
    assert any(e.code == "unknown_dependency" for e in result.errors)


def test_validate_self_dependency() -> None:
    result = validate_graph([_task("t1", "t1")])
    assert not result.ok
    assert any(e.code == "self_dependency" for e in result.errors)


def test_validate_duplicate_id() -> None:
    result = validate_graph([_task("t1"), _task("t1", name="other")])
    assert not result.ok
    assert any(e.code == "duplicate_id" for e in result.errors)


def test_validate_cycle() -> None:
    tasks = [_task("a", "c"), _task("b", "a"), _task("c", "b")]
    result = validate_graph(tasks)
    assert not result.ok
    assert any(e.code == "cycle" for e in result.errors)


def test_validate_ok_diamond() -> None:
    tasks = [
        _task("t1"),
        _task("t2", "t1"),
        _task("t3", "t2"),
        _task("t4", "t2"),
        _task("t5", "t3", "t4"),
        _task("t6", "t3", "t4"),
    ]
    result = validate_graph(tasks)
    assert result.ok
    assert result.errors == []


def test_ready_tasks_initial() -> None:
    tasks = [_task("t1"), _task("t2", "t1"), _task("t3", "t1")]
    ready = ready_tasks(tasks, completed_ids=set())
    assert [t.id for t in ready] == ["t1"]


def test_ready_tasks_after_root() -> None:
    tasks = [_task("t1"), _task("t2", "t1"), _task("t3", "t1"), _task("t4", "t2", "t3")]
    ready = ready_tasks(tasks, completed_ids={"t1"})
    assert [t.id for t in ready] == ["t2", "t3"]


def test_parallel_cohorts_diamond() -> None:
    tasks = [
        _task("t1"),
        _task("t2", "t1"),
        _task("t3", "t2"),
        _task("t4", "t2"),
        _task("t5", "t3", "t4"),
    ]
    cohorts = parallel_cohorts(tasks)
    assert [[t.id for t in c] for c in cohorts] == [
        ["t1"],
        ["t2"],
        ["t3", "t4"],
        ["t5"],
    ]


def test_render_mermaid_includes_edges() -> None:
    text = render_mermaid([_task("t1"), _task("t2", "t1")])
    assert "t1 --> t2" in text
    assert "flowchart TD" in text
