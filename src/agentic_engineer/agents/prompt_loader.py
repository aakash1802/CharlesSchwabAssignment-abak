"""Load agent prompt text files next to this package."""

from __future__ import annotations

from pathlib import Path

_PROMPTS = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    path = _PROMPTS / name
    return path.read_text(encoding="utf-8")
