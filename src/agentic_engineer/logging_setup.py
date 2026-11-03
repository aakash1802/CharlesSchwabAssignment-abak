"""Structured logging setup for the CLI."""

from __future__ import annotations

import logging
import sys
from typing import Any


class _KeyValueFormatter(logging.Formatter):
    """Emit `message` plus stable key=value extras for grep-friendly logs."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras: dict[str, Any] = {}
        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                extras[key] = value
        if not extras:
            return base
        suffix = " ".join(f"{k}={v!r}" for k, v in sorted(extras.items()))
        return f"{base} | {suffix}"


def _quiet_noisy_libraries(root_level: str) -> None:
    """Keep HTTP client chatter out of the default console (progress lines own that)."""
    # DEBUG/-v should still show transport detail.
    quiet = logging.DEBUG if root_level.upper() == "DEBUG" else logging.WARNING
    for name in ("httpx", "httpcore", "anthropic", "urllib3"):
        logging.getLogger(name).setLevel(quiet)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger once for CLI processes."""
    root = logging.getLogger()
    if getattr(root, "_agentic_configured", False):
        root.setLevel(level.upper())
        _quiet_noisy_libraries(level)
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        _KeyValueFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    _quiet_noisy_libraries(level)
    root._agentic_configured = True  # type: ignore[attr-defined]
