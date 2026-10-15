"""Run the original contract; preserve the upstream service's public wire format."""
from pathlib import Path
import subprocess
import sys

workspace, original = map(Path, sys.argv[1:3])
if (workspace / "service.py").read_bytes() != (original / "service.py").read_bytes():
    raise SystemExit("The service wire format must remain unchanged")
result = subprocess.run(
    [sys.executable, "-B", "-c", (original / "test_adapter.py").read_text()],
    cwd=workspace, capture_output=True, text=True, timeout=5,
)
print(result.stdout + result.stderr)
raise SystemExit(int(result.returncode != 0))
