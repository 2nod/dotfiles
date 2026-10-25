from pathlib import Path
import subprocess
import sys

workspace, fixture = map(Path, sys.argv[1:3])
result = subprocess.run(
    [sys.executable, "-B", "-c", (fixture / "test_audit.py").read_text()],
    cwd=workspace, capture_output=True, text=True, timeout=5,
)
print(result.stdout + result.stderr)
raise SystemExit(int(result.returncode != 0))
