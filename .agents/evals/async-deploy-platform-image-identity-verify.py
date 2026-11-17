from pathlib import Path
import subprocess
import sys
workspace, fixture = map(Path, sys.argv[1:3])
if (workspace / 'test.cjs').read_bytes() != (fixture / 'test.cjs').read_bytes():
    raise SystemExit('test.cjs must remain unchanged')
result = subprocess.run(['node', 'test.cjs'], cwd=workspace, capture_output=True, text=True, timeout=5)
print(result.stdout + result.stderr)
completed = '6 artifact identity checks passed' in result.stdout
raise SystemExit(int(result.returncode != 0 or not completed))
