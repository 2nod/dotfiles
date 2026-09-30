#!/usr/bin/env python3
"""Deterministic scope and source-fact gate; read boundaries use behavior_checks."""
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
expected = {"scope": "repository", "branch": "feature/sample",
            "changed_files": ["src/widget.py"], "checks": "not_run"}
try:
    actual = json.loads((root / "result.json").read_text())
except (OSError, ValueError):
    raise SystemExit(1)
raise SystemExit(0 if actual == expected else 1)
