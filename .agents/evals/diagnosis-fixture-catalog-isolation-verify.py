"""Replay the frozen public symptom check against the edited factory."""
from pathlib import Path
import subprocess
import sys

workspace, original = map(Path, sys.argv[1:3])
result = subprocess.run(
    [sys.executable, '-B', '-c', (original / 'test_catalog.py').read_text()],
    cwd=workspace, capture_output=True, text=True, timeout=5,
)
print(result.stdout + result.stderr)
raise SystemExit(int(result.returncode != 0))
