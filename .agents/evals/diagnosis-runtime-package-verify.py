"""Keep the public startup check independent of edits in the candidate workspace."""
from pathlib import Path
import subprocess
import sys

workspace, fixture = map(Path, sys.argv[1:3])
result = subprocess.run(
    [sys.executable, "-B", "-c", (fixture / "check_start.py").read_text()],
    cwd=workspace, capture_output=True, text=True, timeout=10,
)
print(result.stdout + result.stderr)
raise SystemExit(int(result.returncode != 0))
