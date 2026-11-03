"""Build and compile the execution StateGraph (Phases 4–5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from agentic_engineer.graph.nodes_execution import (
    ExecutionContext,
    make_docs_stub_node,
    make_execute_node,
    make_fail_analyze_node,
    make_inspect_node,
    make_replan_park_node,
    make_safe_stop_node,
    make_schedule_node,
    make_sync_node,
)
from agentic_engineer.graph.routing import (
    route_after_execute,
    route_after_fail_analyze,
    route_after_schedule,
    route_after_sync,
)
from agentic_engineer.graph.state import ExecutionGraphState


def checkpoint_db_path(workflow_dir: Path) -> Path:
    checkpoints = workflow_dir / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    return checkpoints / "langgraph.sqlite"


def open_checkpointer(workflow_dir: Path) -> tuple[SqliteSaver, Any]:
    """File-backed SQLite checkpointer under `.agentic/workflows/<id>/checkpoints/`.

    Returns ``(saver, conn)`` — caller must keep ``conn`` alive for the graph lifetime.
    """
    import sqlite3

    db = checkpoint_db_path(workflow_dir)
    conn = sqlite3.connect(str(db), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver, conn


def build_execution_graph(ctx: ExecutionContext) -> Any:
    graph = StateGraph(ExecutionGraphState)
    graph.add_node("inspect", make_inspect_node(ctx))
    graph.add_node("schedule", make_schedule_node(ctx))
    graph.add_node("execute_task", make_execute_node(ctx))
    graph.add_node("sync", make_sync_node(ctx))
    graph.add_node("fail_analyze", make_fail_analyze_node(ctx))
    graph.add_node("docs_stub", make_docs_stub_node(ctx))
    graph.add_node("replan_park", make_replan_park_node(ctx))
    graph.add_node("safe_stop", make_safe_stop_node(ctx))

    graph.set_entry_point("inspect")
    graph.add_edge("inspect", "schedule")
    graph.add_conditional_edges(
        "schedule",
        route_after_schedule,
        {
            "execute_task": "execute_task",
            "complete": "docs_stub",
            "safe_stop": "safe_stop",
        },
    )
    graph.add_conditional_edges(
        "execute_task",
        route_after_execute,
        {
            "execute_task": "execute_task",
            "sync": "sync",
            "fail_analyze": "fail_analyze",
            "await_command": "fail_analyze",
            "await_destructive": "fail_analyze",
        },
    )
    graph.add_conditional_edges(
        "sync",
        route_after_sync,
        {
            "schedule": "schedule",
            "docs_stub": "docs_stub",
            "safe_stop": "safe_stop",
        },
    )
    graph.add_conditional_edges(
        "fail_analyze",
        route_after_fail_analyze,
        {
            "schedule": "schedule",
            "safe_stop": "safe_stop",
            "replan_park": "replan_park",
        },
    )
    graph.add_edge("docs_stub", END)
    graph.add_edge("replan_park", END)
    graph.add_edge("safe_stop", END)
    return graph
