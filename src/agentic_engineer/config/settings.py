"""Global CLI settings (env / optional config). No target workflow state here."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        description="Default model name (e.g. claude-sonnet-4-5 for anthropic)",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="Provider API key; never commit. AGENTIC_LLM_API_KEY or ANTHROPIC_API_KEY.",
    )
    llm_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Per-request LLM timeout",
    )
    llm_max_tokens: int = Field(default=4096, ge=1)
    max_task_retries: int = Field(default=2, ge=0, description="Automatic retry cap")
    command_timeout_seconds: float = Field(default=120.0, gt=0)

    @field_validator("llm_provider")
    @classmethod
    def _normalize_provider(cls, value: str) -> str:
        return value.strip().lower()

    def resolved_llm_api_key(self) -> str | None:
        """Prefer AGENTIC_LLM_API_KEY; fall back to ANTHROPIC_API_KEY for Anthropic UX."""
        if self.llm_api_key:
            return self.llm_api_key
        return os.environ.get("ANTHROPIC_API_KEY") or None

    def resolved_llm_model(self) -> str:
        if self.llm_provider == "anthropic" and self.llm_model in {"", "mock-model"}:
            return "claude-sonnet-4-5"
        return self.llm_model


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Test helper — clear cached settings after env changes."""
    get_settings.cache_clear()
