"""Protected diagnostic records for Developer Agent LLM attempts."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_engineer.workspace.workspace import Workspace

logger = logging.getLogger(__name__)

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*['\"]?([^\s'\"]+)"
)
_MAX_RAW_CHARS = 12_000


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def redact_secrets(text: str) -> str:
    return _SECRET_RE.sub(r"\1=***REDACTED***", text or "")


def _truncate(text: str, limit: int = _MAX_RAW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…[truncated {len(text) - limit} chars]…"


def record_developer_attempt(
    workspace: Workspace,
    *,
    task_id: str,
    attempt: int,
    provider: str,
    model: str,
    stop_reason: str | None,
    token_usage: dict[str, Any] | None,
    response_type: str,
    parsing_outcome: str,
    validation_outcome: str,
    failure_category: str | None,
    retry_decision: str,
    raw_response: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Path | None:
    """
    Persist a redacted diagnostic JSON under `.agentic/artifacts/diagnostics/`.

    Raw model text is stored only here (truncated + secret-redacted), not in
    normal audit event messages.
    """
    try:
        diag_dir = workspace.resolve(".agentic/artifacts/diagnostics")
        diag_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "task_id": task_id,
            "attempt": attempt,
            "provider": provider,
            "model": model,
            "stop_reason": stop_reason,
            "token_usage": token_usage or {},
            "response_type": response_type,
            "parsing_outcome": parsing_outcome,
            "validation_outcome": validation_outcome,
            "failure_category": failure_category,
            "retry_decision": retry_decision,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            payload["extra"] = extra
        if raw_response is not None:
            payload["raw_response_redacted"] = _truncate(redact_secrets(raw_response))
        path = diag_dir / f"{task_id}_attempt{attempt}_{_utc_stamp()}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
    except Exception as exc:  # noqa: BLE001 — diagnostics must never break execution
        logger.debug("developer_diagnostic_write_failed: %s", exc)
        return None
