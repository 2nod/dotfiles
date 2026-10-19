"""Verify error identity against the unchanged public adapter and original tests."""
from pathlib import Path
import subprocess
import sys

workspace, original = map(Path, sys.argv[1:3])
if (workspace / "adapter.cjs").read_bytes() != (original / "adapter.cjs").read_bytes():
    raise SystemExit("Preserve the public response adapter")
result = subprocess.run(
    ["node", "-e", (original / "test.cjs").read_text()],
    cwd=workspace, capture_output=True, text=True, timeout=5,
)
print(result.stdout + result.stderr)
raise SystemExit(int(result.returncode != 0))
