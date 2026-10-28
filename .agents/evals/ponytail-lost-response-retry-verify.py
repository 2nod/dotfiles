from pathlib import Path
import subprocess
import sys
workspace, fixture = map(Path, sys.argv[1:3])
for name in ('transport.cjs', 'test.cjs'):
    if (workspace / name).read_bytes() != (fixture / name).read_bytes():
        raise SystemExit(f'{name} must remain unchanged')
r = subprocess.run(['node', 'test.cjs'], cwd=workspace, capture_output=True, text=True, timeout=5)
print(r.stdout + r.stderr)
raise SystemExit(r.returncode)
