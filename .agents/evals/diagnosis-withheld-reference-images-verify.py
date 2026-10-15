from pathlib import Path
import subprocess
import sys

workspace, fixture = map(Path, sys.argv[1:3])
try:
    result = subprocess.run([sys.executable, '-B', '-c', (fixture / 'test_review.py').read_text()], cwd=workspace, capture_output=True, text=True, timeout=5)
except subprocess.TimeoutExpired:
    print('Review packet validation did not finish')
    raise SystemExit(1)
print(result.stdout + result.stderr)
raise SystemExit(int(result.returncode != 0))
