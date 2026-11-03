"""Global CLI settings (env / config file / optional .env). No target workflow state here."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Type

from pydantic import Field, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from agentic_engineer.config.file_config import (
    load_config_file_values,
    set_config_file_override,
)


class _TomlFileSettingsSource(PydanticBaseSettingsSource):
    """Load settings from discovered/override TOML after env, before defaults."""

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        data = load_config_file_values()
        return data.get(field_name), field_name, False

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        data = load_config_file_values()
        allowed = self.settings_cls.model_fields
        return {k: v for k, v in data.items() if k in allowed and v is not None}


class Settings(BaseSettings):
    """Process-wide CLI configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AGENTIC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO", description="Logging level")
    llm_provider: str = Field(
        default="mock",
        description="LLM provider id: mock | anthropic",
    )
    llm_model: str = Field(
        default="mock-model",
        description="Default model name (e.g. claude-sonnet-5-5 for anthropic)",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="Provider API key; never commit. File, AGENTIC_LLM_API_KEY, or ANTHROPIC_API_KEY.",
    )
    llm_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Per-request LLM timeout",
    )
    llm_max_tokens: int = Field(default=4096, ge=1)
    max_task_retries: int = Field(default=2, ge=0, description="Automatic retry cap")
    max_structured_retries: int = Field(
        default=2,
        ge=0,
        description="Tighter auto-retry cap for structured-output / truncation failures",
    )
    developer_max_files_per_batch: int = Field(
        default=5,
        ge=1,
        description="Max files the Developer Agent may emit per LLM batch",
    )
    developer_max_batches: int = Field(
        default=4,
        ge=1,
        description="Max Developer Agent generation batches per task",
    )
    developer_structured_attempts: int = Field(
        default=2,
        ge=1,
        description="Bounded regenerations inside a Developer Agent batch",
    )
    command_timeout_seconds: float = Field(default=120.0, gt=0)

    @field_validator("llm_provider")
    @classmethod
    def _normalize_provider(cls, value: str) -> str:
        return value.strip().lower()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority (high → low): init, env, .env, TOML config file, secrets.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            _TomlFileSettingsSource(settings_cls),
            file_secret_settings,
        )

    def resolved_llm_api_key(self) -> str | None:
        """Prefer settings/env AGENTIC key; fall back to ANTHROPIC_API_KEY."""
        if self.llm_api_key:
            return self.llm_api_key
        return os.environ.get("ANTHROPIC_API_KEY") or None

    def resolved_llm_model(self) -> str:
        if self.llm_provider == "anthropic" and self.llm_model in {"", "mock-model"}:
            return "claude-sonnet-5-5"
        return self.llm_model


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings after env/config changes."""
    get_settings.cache_clear()


def configure_from_cli(*, config_file: str | Path | None = None) -> Settings:
    """Apply `--config` override and rebuild cached settings."""
    set_config_file_override(config_file)
    clear_settings_cache()
    return get_settings()
