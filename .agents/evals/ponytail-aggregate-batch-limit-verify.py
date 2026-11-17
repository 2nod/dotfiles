from pathlib import Path
import subprocess
import sys
workspace, fixture = map(Path, sys.argv[1:3])
for name in ('rules.cjs', 'test.cjs'):
    if (workspace / name).read_bytes() != (fixture / name).read_bytes():
        raise SystemExit(f'{name} must remain unchanged')
result = subprocess.run(['node', 'test.cjs'], cwd=workspace, capture_output=True, text=True, timeout=5)
print(result.stdout + result.stderr)
completed = 'Per-batch limits and aggregated receipt restoration pass.' in result.stdout
raise SystemExit(int(result.returncode != 0 or not completed))
