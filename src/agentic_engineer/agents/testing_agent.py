"""Testing agent — propose commands; never run them directly."""

from __future__ import annotations

import json

from agentic_engineer.agents.codegen_context import CodegenContext, is_mock_without_queue
from agentic_engineer.agents.prompt_loader import load_prompt
from agentic_engineer.execution.commands import CommandRunner
from agentic_engineer.llm.base import LLMError, LLMProvider, LLMRequest
from agentic_engineer.llm.json_extract import describe_json_error, extract_json_text
from agentic_engineer.models.execution import CommandProposal
from agentic_engineer.models.task import Task


def _stub_proposal(runner: CommandRunner, task: Task) -> CommandProposal:
    return runner.propose_argv(
        ["python", "-c", f"print('test-ok:{task.id}')"],
        reason=f"Validate task {task.id}: {task.name}",
        task_id=task.id,
    )


class TestingAgent:
    __test__ = False  # not a pytest test class

    def __init__(self, provider: LLMProvider, runner: CommandRunner) -> None:
        self._provider = provider
        self._runner = runner
        self._system = load_prompt("testing_agent.txt")

    def propose_for_task(
        self,
        task: Task,
        *,
        context: CodegenContext | None = None,
    ) -> CommandProposal:
        """Propose a validation command for the task (human must approve before run)."""
        if is_mock_without_queue(self._provider):
            return _stub_proposal(self._runner, task)

        ctx = context or CodegenContext(task=task)
        request = LLMRequest(
            prompt=ctx.to_prompt_json() + "\n\nReturn JSON only.",
            system=self._system,
            response_schema_name="CommandProposal",
        )
        try:
            response = self._provider.complete(request)
            data = json.loads(extract_json_text(response.text))
            if not isinstance(data, dict):
                raise ValueError("Command proposal must be a JSON object")
            reason = str(data.get("reason") or f"Validate task {task.id}").strip()
            cwd = str(data.get("cwd_relative") or ".").strip() or "."
            kind = str(data.get("kind") or "argv").strip().lower()
            if kind == "shell":
                shell = str(data.get("shell") or "").strip()
                if not shell:
                    raise ValueError("shell kind requires a non-empty shell string")
                return self._runner.propose_shell(
                    shell, reason=reason, task_id=task.id, cwd_relative=cwd
                )
            argv_raw = data.get("argv")
            if not isinstance(argv_raw, list) or not argv_raw:
                raise ValueError("argv kind requires a non-empty argv list")
            argv = [str(part) for part in argv_raw]
            return self._runner.propose_argv(
                argv, reason=reason, task_id=task.id, cwd_relative=cwd
            )
        except (LLMError, json.JSONDecodeError, ValueError, TypeError) as exc:
            detail = describe_json_error(exc) if isinstance(exc, json.JSONDecodeError) else str(exc)
            raise LLMError(
                f"Testing agent failed for {task.id} ({task.name}): {detail}"
            ) from exc
