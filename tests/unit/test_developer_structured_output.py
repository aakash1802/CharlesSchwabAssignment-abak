"""Developer Agent structured output, validation, and retry classification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_engineer.agents.codegen_context import CodegenContext
from agentic_engineer.agents.developer_agent import DeveloperAgent
from agentic_engineer.agents.failure_analysis_agent import FailureAnalysisAgent
from agentic_engineer.agents.file_commit import validate_generated_files
from agentic_engineer.config.settings import clear_settings_cache
from agentic_engineer.llm import ClassifiedLLMError, FailureCategory, LLMResponse, MockProvider
from agentic_engineer.llm.anthropic_provider import AnthropicProvider
from agentic_engineer.llm.base import LLMRequest
from agentic_engineer.llm.structured_parse import parse_structured_model
from agentic_engineer.models.developer import DeveloperFilesResponse, GeneratedFile
from agentic_engineer.models.task import Task
from agentic_engineer.workspace import Workspace


def _task(task_id: str = "t2") -> Task:
    return Task(
        id=task_id,
        name="Scaffold",
        description="Create project scaffolding",
        agent="developer",
        acceptance_criteria=["config loads"],
    )


def _valid_payload(**overrides: object) -> dict:
    data = {
        "summary": "scaffold",
        "files": [
            {"path": "app/main.py", "content": "def main():\n    return 1\n", "action": "create"},
            {"path": "pyproject.toml", "content": "[project]\nname='demo'\n", "action": "create"},
        ],
        "implementation_decisions": ["Use FastAPI"],
        "warnings": [],
        "more_files_remaining": False,
    }
    data.update(overrides)
    return data


def test_valid_structured_response_writes_files(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "ok")
    agent = DeveloperAgent(MockProvider(responses=[json.dumps(_valid_payload())]))
    result = agent.apply_task(workspace=ws, task=_task(), context=CodegenContext(task=_task()))
    assert result.written_paths == ["app/main.py", "pyproject.toml"]
    assert (ws.root / "app" / "main.py").is_file()
    assert any("FastAPI" in d for d in result.implementation_decisions)


def test_malformed_json_classified(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "bad_json")
    agent = DeveloperAgent(MockProvider(responses=["not-json {{{"]))
    with pytest.raises(ClassifiedLLMError) as excinfo:
        agent.apply_task(workspace=ws, task=_task())
    assert excinfo.value.category == FailureCategory.INVALID_STRUCTURED_OUTPUT
    assert not (ws.root / "app").exists()


def test_truncated_response_stop_reason(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "trunc")
    response = LLMResponse(
        text='{"summary":"x","files":[{"path":"a.py","content":"def f(',
        model="mock-model",
        stop_reason="max_tokens",
        response_type="truncated",
        raw={"stop_reason": "max_tokens", "usage": {"output_tokens": 4096}},
        usage={"output_tokens": 4096},
    )
    # Second attempt succeeds with reduced scope.
    agent = DeveloperAgent(
        MockProvider(
            responses=[
                response,
                json.dumps(_valid_payload(files=[{"path": "a.py", "content": "x=1\n"}])),
            ]
        )
    )
    result = agent.apply_task(workspace=ws, task=_task())
    assert result.written_paths == ["a.py"]


def test_empty_response(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "empty")
    agent = DeveloperAgent(
        MockProvider(
            responses=[
                LLMResponse(text="", model="mock", response_type="empty"),
            ]
        )
    )
    with pytest.raises(ClassifiedLLMError) as excinfo:
        agent.apply_task(workspace=ws, task=_task())
    assert excinfo.value.category == FailureCategory.INVALID_STRUCTURED_OUTPUT


def test_unexpected_response_block(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "unexpected")
    from types import SimpleNamespace

    message = SimpleNamespace(
        id="msg",
        model="claude-sonnet-5-5",
        stop_reason="end_turn",
        content=[SimpleNamespace(type="mystery", text=None)],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: message))
    provider = AnthropicProvider(api_key="test-key", client=client)
    with pytest.raises(ClassifiedLLMError) as excinfo:
        provider.complete(
            LLMRequest(
                prompt="hi",
                response_schema_name="DeveloperFiles",
            )
        )
    assert excinfo.value.category == FailureCategory.INVALID_STRUCTURED_OUTPUT
    assert not list((ws.root).glob("**/*.py"))


def test_schema_mismatch(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "schema")
    agent = DeveloperAgent(
        MockProvider(responses=[json.dumps({"summary": "x", "files": "nope"})])
    )
    with pytest.raises(ClassifiedLLMError) as excinfo:
        agent.apply_task(workspace=ws, task=_task())
    assert excinfo.value.category == FailureCategory.SCHEMA_VALIDATION
    assert not (ws.root / "app").exists()


def test_invalid_file_path() -> None:
    with pytest.raises(Exception):
        GeneratedFile(path="", content="x")


def test_workspace_escape_attempt(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "escape")
    staged_files = [
        GeneratedFile(path="../outside.py", content="hacked"),
    ]
    with pytest.raises(ClassifiedLLMError) as excinfo:
        validate_generated_files(ws, staged_files, max_files=5)
    assert excinfo.value.category == FailureCategory.WORKSPACE_SAFETY
    assert not (tmp_path / "outside.py").exists()


def test_provider_timeout_classified(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "timeout")
    agent = DeveloperAgent(
        MockProvider(
            responses=[
                ClassifiedLLMError(
                    "Anthropic request failed: timeout",
                    category=FailureCategory.TRANSIENT_PROVIDER,
                )
            ]
        )
    )
    with pytest.raises(ClassifiedLLMError) as excinfo:
        agent.apply_task(workspace=ws, task=_task())
    assert excinfo.value.category == FailureCategory.TRANSIENT_PROVIDER


def test_rate_limiting_failure_analysis() -> None:
    clear_settings_cache()
    agent = FailureAnalysisAgent(MockProvider())
    task = _task()
    task.retry_count = 0
    result = agent.analyze(
        task=task,
        error="429 Too Many Requests",
        max_retries=2,
        failure_category=FailureCategory.RATE_LIMIT,
    )
    assert result.recommendation == "retry"
    assert result.failure_category == FailureCategory.RATE_LIMIT
    assert "Rate limited" in result.reason


def test_targeted_regeneration_after_structured_failure(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "regen")
    agent = DeveloperAgent(
        MockProvider(
            responses=[
                "not-json",
                json.dumps(_valid_payload()),
            ]
        )
    )
    result = agent.apply_task(workspace=ws, task=_task())
    assert result.written_paths == ["app/main.py", "pyproject.toml"]


def test_retry_exhaustion_for_structured_output() -> None:
    clear_settings_cache()
    agent = FailureAnalysisAgent(MockProvider())
    task = _task()
    task.retry_count = 2
    result = agent.analyze(
        task=task,
        error="[failure_category=invalid_structured_output] bad json",
        max_retries=5,
        failure_category=FailureCategory.INVALID_STRUCTURED_OUTPUT,
    )
    # structured cap default is 2; retry_count already 2 → stop
    assert result.recommendation == "stop"
    assert "category=invalid_structured_output" in result.reason


def test_no_filesystem_modification_when_validation_fails(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "novwrite")
    marker = ws.root / "preexisting.txt"
    marker.write_text("keep", encoding="utf-8")
    payload = _valid_payload(
        files=[
            {"path": "ok.py", "content": "x=1\n", "action": "create"},
            {"path": "../escape.py", "content": "nope", "action": "create"},
        ]
    )
    # Force through parse then fail validation — use structured dict that
    # validates pydantic but fails workspace checks.
    # Empty path fails pydantic; escape fails workspace.
    agent = DeveloperAgent(MockProvider(responses=[json.dumps(payload)]))
    with pytest.raises(ClassifiedLLMError) as excinfo:
        agent.apply_task(workspace=ws, task=_task())
    assert excinfo.value.category == FailureCategory.WORKSPACE_SAFETY
    assert marker.read_text(encoding="utf-8") == "keep"
    assert not (ws.root / "ok.py").exists()


def test_parse_structured_model_accepts_provider_structured() -> None:
    response = LLMResponse(
        text="",
        model="m",
        structured=_valid_payload(),
        response_type="structured_json",
    )
    parsed = parse_structured_model(response, DeveloperFilesResponse)
    assert len(parsed.files) == 2


def test_workspace_safety_is_non_retryable() -> None:
    agent = FailureAnalysisAgent(MockProvider())
    task = _task()
    result = agent.analyze(
        task=task,
        error="escape",
        max_retries=5,
        failure_category=FailureCategory.WORKSPACE_SAFETY,
    )
    assert result.recommendation == "stop"
    assert "Non-retryable" in result.reason


def test_batched_generation(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "batch")
    batch1 = _valid_payload(
        files=[{"path": "a.py", "content": "a=1\n", "action": "create"}],
        more_files_remaining=True,
        summary="batch1",
    )
    batch2 = _valid_payload(
        files=[{"path": "b.py", "content": "b=1\n", "action": "create"}],
        more_files_remaining=False,
        summary="batch2",
    )
    agent = DeveloperAgent(
        MockProvider(responses=[json.dumps(batch1), json.dumps(batch2)])
    )
    result = agent.apply_task(workspace=ws, task=_task())
    assert result.written_paths == ["a.py", "b.py"]
    assert (ws.root / "a.py").is_file()
    assert (ws.root / "b.py").is_file()
