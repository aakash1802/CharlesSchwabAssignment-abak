"""Unit tests for LLM-driven developer / testing / documentation agents."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_engineer.agents.codegen_context import (
    CodegenContext,
    normalize_relative_path,
    parse_files_payload,
)
from agentic_engineer.agents.developer_agent import DeveloperAgent
from agentic_engineer.agents.documentation_agent import DocumentationAgent
from agentic_engineer.agents.testing_agent import TestingAgent
from agentic_engineer.execution.commands import CommandRunner
from agentic_engineer.llm import LLMError, MockProvider
from agentic_engineer.models.plan import EngineeringPlan
from agentic_engineer.models.specification import Specification
from agentic_engineer.models.task import Task
from agentic_engineer.workspace import Workspace


def _task(task_id: str = "t3") -> Task:
    return Task(
        id=task_id,
        name="Implement API",
        description="Add FastAPI endpoints",
        agent="developer",
        acceptance_criteria=["POST works"],
    )


def test_normalize_relative_path_rejects_escapes() -> None:
    assert normalize_relative_path("src/app.py") == "src/app.py"
    with pytest.raises(ValueError):
        normalize_relative_path("../outside.py")
    with pytest.raises(ValueError):
        normalize_relative_path(".agentic/secret.json")
    with pytest.raises(ValueError):
        normalize_relative_path("C:/Windows/x.py")


def test_parse_files_payload() -> None:
    files = parse_files_payload(
        {"files": [{"path": "README.md", "content": "# Hi\n"}]}
    )
    assert files == [("README.md", "# Hi\n")]
    with pytest.raises(ValueError):
        parse_files_payload({"files": []})


def test_developer_mock_fallback_writes_stub(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "dev_stub")
    agent = DeveloperAgent(MockProvider())
    result = agent.apply_task(workspace=ws, task=_task("t3"))
    assert result.written_paths == ["src/generated/t3.py"]
    assert (ws.root / "src" / "generated" / "t3.py").is_file()


def test_developer_llm_writes_queued_files(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "dev_llm")
    payload = {
        "summary": "scaffold app",
        "files": [
            {"path": "app/main.py", "content": "def ping():\n    return 'ok'\n"},
            {"path": "pyproject.toml", "content": "[project]\nname='demo'\n"},
        ],
    }
    agent = DeveloperAgent(MockProvider(responses=[json.dumps(payload)]))
    result = agent.apply_task(
        workspace=ws,
        task=_task(),
        context=CodegenContext(task=_task()),
    )
    assert result.written_paths == ["app/main.py", "pyproject.toml"]
    assert (ws.root / "app" / "main.py").read_text(encoding="utf-8").startswith("def ping")
    assert result.summary == "scaffold app"


def test_developer_llm_rejects_bad_json(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "dev_bad")
    agent = DeveloperAgent(MockProvider(responses=["not-json"]))
    with pytest.raises(LLMError, match="Developer agent failed for t3"):
        agent.apply_task(workspace=ws, task=_task())


def test_developer_llm_rejects_unterminated_json(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "dev_trunc")
    truncated = '{"summary": "x", "files": [{"path": "a.py", "content": "def f():\\n'
    agent = DeveloperAgent(MockProvider(responses=[truncated]))
    with pytest.raises(LLMError, match="invalid JSON|truncated|Unterminated"):
        agent.apply_task(workspace=ws, task=_task())


def test_testing_mock_fallback_argv(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "test_stub")
    agent = TestingAgent(MockProvider(), CommandRunner(ws))
    proposal = agent.propose_for_task(_task("t6"))
    assert proposal.kind == "argv"
    assert proposal.argv == ["python", "-c", "print('test-ok:t6')"]


def test_testing_llm_proposes_pytest(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "test_llm")
    payload = {
        "reason": "Run unit tests",
        "kind": "argv",
        "argv": ["python", "-m", "pytest", "-q"],
        "cwd_relative": ".",
    }
    agent = TestingAgent(
        MockProvider(responses=[json.dumps(payload)]),
        CommandRunner(ws),
    )
    proposal = agent.propose_for_task(_task("t6"), context=CodegenContext(task=_task("t6")))
    assert proposal.argv == ["python", "-m", "pytest", "-q"]
    assert "unit tests" in proposal.reason.lower()


def test_testing_llm_shell_kind(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "test_shell")
    payload = {
        "reason": "install and test",
        "kind": "shell",
        "shell": "python -m pytest -q",
    }
    agent = TestingAgent(
        MockProvider(responses=[json.dumps(payload)]),
        CommandRunner(ws),
    )
    proposal = agent.propose_for_task(_task())
    assert proposal.kind == "shell"
    assert proposal.shell == "python -m pytest -q"


def test_documentation_llm_writes_readme(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "docs_llm")
    payload = {
        "summary": "readme",
        "files": [{"path": "README.md", "content": "# Demo\n\nSetup steps.\n"}],
    }
    agent = DocumentationAgent(MockProvider(responses=[json.dumps(payload)]))
    paths = agent.write_task_notes(
        workspace=ws,
        task=Task(id="t7", name="Docs", agent="documentation"),
        context=CodegenContext(task=Task(id="t7", name="Docs")),
    )
    assert paths == ["README.md"]
    assert "Setup steps" in (ws.root / "README.md").read_text(encoding="utf-8")


def test_documentation_mock_product_notes(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "docs_stub")
    plan = EngineeringPlan(
        id="plan_x",
        workflow_id="wf",
        specification_id="spec_x",
        summary="Build demo",
        tasks=[_task()],
    )
    paths = DocumentationAgent(MockProvider()).write_product_notes(
        workspace=ws, plan=plan, design_note="note"
    )
    assert paths == ["docs/AGENTIC_NOTES.md"]
    text = (ws.root / "docs" / "AGENTIC_NOTES.md").read_text(encoding="utf-8")
    assert "Build demo" in text


def test_documentation_product_notes_llm(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "docs_prod")
    payload = {
        "files": [
            {"path": "README.md", "content": "# App\n"},
            {"path": "docs/USAGE.md", "content": "# Usage\n"},
        ]
    }
    plan = EngineeringPlan(
        id="plan_y",
        workflow_id="wf",
        specification_id="spec_y",
        summary="URL shortener",
        tasks=[],
    )
    spec = Specification(
        id="spec_y",
        workflow_id="wf",
        title="URL Shortener",
        summary="Shorten URLs",
    )
    agent = DocumentationAgent(MockProvider(responses=[json.dumps(payload)]))
    paths = agent.write_product_notes(
        workspace=ws, plan=plan, design_note="layered", specification=spec
    )
    assert "README.md" in paths
    assert "docs/USAGE.md" in paths
