#!/usr/bin/env python
"""
Convenience launcher for local testing (no .exe / no python -m required).

Usage (from repo root, with venv Python):

    python agenticli_test.py --help
    python agenticli_test.py version
    python agenticli_test.py init ..\\phase2-test-target
    python agenticli_test.py --config agentic.toml run ..\\phase2-test-target --requirement "Improve sharing security"
    python agenticli_test.py run ..\\phase2-test-target --requirement-file .\\requirement.md

Credentials/model: copy agentic.config.example.toml → agentic.toml (gitignored),
or use ~/.agentic/config.toml. See docs/phase2/LLM_CONFIGURATION.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running without an editable install by putting src/ on sys.path.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agentic_engineer.cli.main import app

if __name__ == "__main__":
    app()
