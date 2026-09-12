#!/usr/bin/env python3
"""Verify concrete file outcomes; trace checks are run separately by the runner."""
import json
from pathlib import Path
import sys

workspace, case_path = map(Path, sys.argv[1:])
case = json.loads(case_path.read_text())
for name, expected in case["behavior"]["files"].items():
    path = workspace / name
    if not path.is_file() or path.read_bytes() != expected.encode():
        raise SystemExit(1)
raise SystemExit(0)
