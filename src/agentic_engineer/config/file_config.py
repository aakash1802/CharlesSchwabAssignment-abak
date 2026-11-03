"""Load global CLI settings from TOML config files (not target `.agentic/` state)."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

# Process-level override from CLI `--config`.
_CONFIG_PATH_OVERRIDE: Path | None = None

CONFIG_FILENAMES = ("agentic.toml", "agentic.config.toml")


def set_config_file_override(path: str | Path | None) -> None:
    """Set/clear explicit config path (used by CLI `--config`)."""
    global _CONFIG_PATH_OVERRIDE
    _CONFIG_PATH_OVERRIDE = Path(path).expanduser().resolve() if path else None


def get_config_file_override() -> Path | None:
    return _CONFIG_PATH_OVERRIDE


def user_config_path() -> Path:
    return Path.home() / ".agentic" / "config.toml"


def discover_config_path(explicit: Path | None = None) -> Path | None:
    """
    Resolve which config file to load.

    Order:
    1. Explicit path (CLI `--config` / override)
    2. AGENTIC_CONFIG env var
    3. ./agentic.toml or ./agentic.config.toml (cwd)
    4. ~/.agentic/config.toml
    """
    if explicit is not None:
        path = explicit.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")
        return path

    if _CONFIG_PATH_OVERRIDE is not None:
        if not _CONFIG_PATH_OVERRIDE.is_file():
            raise FileNotFoundError(f"Config file not found: {_CONFIG_PATH_OVERRIDE}")
        return _CONFIG_PATH_OVERRIDE

    env_path = os.environ.get("AGENTIC_CONFIG")
    if env_path:
        path = Path(env_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"AGENTIC_CONFIG file not found: {path}")
        return path

    cwd = Path.cwd()
    for name in CONFIG_FILENAMES:
        candidate = cwd / name
        if candidate.is_file():
            return candidate.resolve()

    home_cfg = user_config_path()
    if home_cfg.is_file():
        return home_cfg.resolve()

    return None


def flatten_agentic_toml(data: dict[str, Any]) -> dict[str, Any]:
    """
    Map TOML (flat or nested) onto Settings field names.

    Supported shapes:

        llm_provider = "anthropic"

        [llm]
        provider = "anthropic"
        model = "claude-sonnet-5-5"
        api_key = "..."
        timeout_seconds = 60
        max_tokens = 4096

        [execution]
        max_task_retries = 2
        command_timeout_seconds = 120
    """
    out: dict[str, Any] = {}

    direct_keys = {
        "log_level",
        "llm_provider",
        "llm_model",
        "llm_api_key",
        "llm_timeout_seconds",
        "llm_max_tokens",
        "max_task_retries",
        "max_structured_retries",
        "developer_max_files_per_batch",
        "developer_max_batches",
        "developer_structured_attempts",
        "command_timeout_seconds",
    }
    for key in direct_keys:
        if key in data and not isinstance(data[key], dict):
            out[key] = data[key]

    llm = data.get("llm")
    if isinstance(llm, dict):
        mapping = {
            "provider": "llm_provider",
            "model": "llm_model",
            "api_key": "llm_api_key",
            "timeout_seconds": "llm_timeout_seconds",
            "max_tokens": "llm_max_tokens",
        }
        for src, dest in mapping.items():
            if src in llm and dest not in out:
                out[dest] = llm[src]

    execution = data.get("execution")
    if isinstance(execution, dict):
        for key in (
            "max_task_retries",
            "max_structured_retries",
            "developer_max_files_per_batch",
            "developer_max_batches",
            "developer_structured_attempts",
            "command_timeout_seconds",
            "log_level",
        ):
            if key in execution and key not in out:
                out[key] = execution[key]

    return out


def load_config_file_values(explicit: Path | None = None) -> dict[str, Any]:
    path = discover_config_path(explicit)
    if path is None:
        return {}
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a TOML table: {path}")
    return flatten_agentic_toml(raw)
