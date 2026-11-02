"""Atomic JSON store tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from agentic_engineer.persistence import JsonStore, PersistenceError


class Sample(BaseModel):
    schema_version: int = 1
    name: str


def test_atomic_roundtrip(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    store.write_model("doc.json", Sample(name="alpha"))
    loaded = store.read_model("doc.json", Sample)
    assert loaded.name == "alpha"
    assert loaded.schema_version == 1


def test_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    store = JsonStore(tmp_path)
    with pytest.raises(PersistenceError):
        store.read_json("bad.json")


def test_schema_validation_raises(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    store.write_json("doc.json", {"schema_version": 1})
    with pytest.raises(PersistenceError):
        store.read_model("doc.json", Sample)
