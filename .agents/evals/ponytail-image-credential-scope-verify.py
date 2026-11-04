import pathlib
import subprocess
import sys

workspace = pathlib.Path(sys.argv[1])
fixture = pathlib.Path(sys.argv[2])
for name in ('transport.cjs', 'test.cjs'):
    if (workspace / name).read_bytes() != (fixture / name).read_bytes():
        raise SystemExit(f'{name} must remain unchanged')
result = subprocess.run(['node', 'test.cjs'], cwd=workspace, capture_output=True, text=True, timeout=10)
print(result.stdout)
print(result.stderr)
completed = 'Authenticated artwork and signed image credential policies passed' in result.stdout
raise SystemExit(int(result.returncode != 0 or not completed))
