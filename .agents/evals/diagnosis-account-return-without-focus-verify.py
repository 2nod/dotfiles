"""Run immutable public behavior checks without network, credentials or clocks."""
from pathlib import Path
import subprocess
import sys

workspace, original = map(Path, sys.argv[1:3])
result = subprocess.run(
    ['node', '-e', (original / 'test.cjs').read_text()],
    cwd=workspace, capture_output=True, text=True, timeout=5,
)
print(result.stdout + result.stderr)
completed = 'PASS completion refreshes without focus; invalid notifications are ignored' in result.stdout
raise SystemExit(int(result.returncode != 0 or not completed))
