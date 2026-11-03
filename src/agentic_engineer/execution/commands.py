"""CommandRunner — propose any argv/shell; never run without human approve."""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from agentic_engineer.config.settings import get_settings
from agentic_engineer.models.execution import CommandEvidence, CommandProposal
from agentic_engineer.workspace.paths import contained_path
from agentic_engineer.workspace.workspace import Workspace


class CommandRunnerError(Exception):
    """Invalid command proposal or policy violation."""


@dataclass(frozen=True)
class CommandRunner:
    """Run approved commands with cwd confined to the workspace."""

    workspace: Workspace

    def propose_argv(
        self,
        argv: list[str],
        *,
        reason: str = "",
        task_id: str | None = None,
        cwd_relative: str = ".",
    ) -> CommandProposal:
        if not argv or not all(isinstance(part, str) and part for part in argv):
            raise CommandRunnerError("argv must be a non-empty list of non-empty strings")
        self._assert_cwd(cwd_relative)
        return CommandProposal(
            proposal_id=f"cmd_{uuid.uuid4().hex[:10]}",
            kind="argv",
            argv=list(argv),
            shell=None,
            cwd_relative=cwd_relative,
            reason=reason,
            task_id=task_id,
        )

    def propose_shell(
        self,
        shell: str,
        *,
        reason: str = "",
        task_id: str | None = None,
        cwd_relative: str = ".",
    ) -> CommandProposal:
        text = shell.strip()
        if not text:
            raise CommandRunnerError("shell command must not be empty")
        self._assert_cwd(cwd_relative)
        return CommandProposal(
            proposal_id=f"cmd_{uuid.uuid4().hex[:10]}",
            kind="shell",
            argv=[],
            shell=text,
            cwd_relative=cwd_relative,
            reason=reason,
            task_id=task_id,
        )

    def run_approved(self, proposal: CommandProposal) -> CommandEvidence:
        """Execute a previously approved proposal. Never call without human approve."""
        cwd = self._assert_cwd(proposal.cwd_relative)
        timeout = get_settings().command_timeout_seconds
        timed_out = False
        try:
            if proposal.kind == "shell":
                completed = subprocess.run(
                    proposal.shell or "",
                    shell=True,
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            else:
                completed = subprocess.run(
                    proposal.argv,
                    shell=False,
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            exit_code = int(completed.returncode)
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = -1
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else (
                f"Command timed out after {timeout}s"
            )

        return CommandEvidence(
            proposal_id=proposal.proposal_id,
            exit_code=exit_code,
            stdout=_truncate(stdout),
            stderr=_truncate(stderr),
            timed_out=timed_out,
            approved=True,
            task_id=proposal.task_id,
        )

    def rejected_evidence(self, proposal: CommandProposal) -> CommandEvidence:
        return CommandEvidence(
            proposal_id=proposal.proposal_id,
            exit_code=-1,
            stdout="",
            stderr="Command rejected by human; not executed",
            timed_out=False,
            approved=False,
            task_id=proposal.task_id,
        )

    def _assert_cwd(self, cwd_relative: str) -> Path:
        rel = cwd_relative.strip() or "."
        if rel in {".", "./"}:
            return self.workspace.root
        return contained_path(self.workspace.root, rel)


def _truncate(text: str, limit: int = 8000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n...[truncated]..."
