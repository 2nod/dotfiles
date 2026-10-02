"""Use the original public assertions so changing the test cannot hide a bug."""
from pathlib import Path
import subprocess
import sys


workspace, original = map(Path, sys.argv[1:3])
try:
    result = subprocess.run([sys.executable, '-B', '-c', (original / 'test_monitor.py').read_text()],
                            cwd=workspace, capture_output=True, text=True, timeout=5)
except subprocess.TimeoutExpired:
    print('Status computation timed out')
    raise SystemExit(1)
print(result.stdout + result.stderr)
raise SystemExit(int(result.returncode != 0))
