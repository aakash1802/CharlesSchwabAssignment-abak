"""TOML config file loading for CLI settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_engineer.config.file_config import (
    discover_config_path,
    flatten_agentic_toml,
    load_config_file_values,
    set_config_file_override,
)
from agentic_engineer.config.settings import (
    Settings,
    clear_settings_cache,
    configure_from_cli,
)


def test_flatten_nested_llm_section() -> None:
    flat = flatten_agentic_toml(
        {
            "log_level": "DEBUG",
            "llm": {
                "provider": "anthropic",
                "model": "claude-sonnet-5-5",
                "api_key": "sk-ant-test",
                "timeout_seconds": 30,
                "max_tokens": 2048,
            },
            "execution": {"max_task_retries": 1},
        }
    )
    assert flat["llm_provider"] == "anthropic"
    assert flat["llm_api_key"] == "sk-ant-test"
    assert flat["llm_timeout_seconds"] == 30
    assert flat["max_task_retries"] == 1
    assert flat["log_level"] == "DEBUG"


def test_load_and_apply_config_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENTIC_CONFIG", raising=False)
    monkeypatch.delenv("AGENTIC_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("AGENTIC_LLM_API_KEY", raising=False)
    set_config_file_override(None)
    clear_settings_cache()

    cfg = tmp_path / "agentic.toml"
    cfg.write_text(
        """
log_level = "WARNING"

[llm]
provider = "anthropic"
model = "claude-sonnet-5-5"
api_key = "sk-ant-from-file"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert discover_config_path() == cfg.resolve()
    values = load_config_file_values()
    assert values["llm_api_key"] == "sk-ant-from-file"

    settings = configure_from_cli()
    assert settings.llm_provider == "anthropic"
    assert settings.resolved_llm_api_key() == "sk-ant-from-file"
    assert settings.log_level == "WARNING"

    set_config_file_override(None)
    clear_settings_cache()


def test_env_overrides_config_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENTIC_CONFIG", raising=False)
    set_config_file_override(None)
    clear_settings_cache()

    (tmp_path / "agentic.toml").write_text(
        '[llm]\nprovider = "anthropic"\napi_key = "from-file"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTIC_LLM_PROVIDER", "mock")
    monkeypatch.setenv("AGENTIC_LLM_API_KEY", "from-env")

    settings = Settings()
    assert settings.llm_provider == "mock"
    assert settings.llm_api_key == "from-env"

    clear_settings_cache()
    monkeypatch.delenv("AGENTIC_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("AGENTIC_LLM_API_KEY", raising=False)


def test_explicit_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    other = tmp_path / "custom.toml"
    other.write_text(
        '[llm]\nprovider = "anthropic"\napi_key = "custom-key"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("AGENTIC_LLM_API_KEY", raising=False)
    settings = configure_from_cli(config_file=other)
    assert settings.resolved_llm_api_key() == "custom-key"
    set_config_file_override(None)
    clear_settings_cache()
