import pathlib
import subprocess
import sys

workspace = pathlib.Path(sys.argv[1])
fixture = pathlib.Path(sys.argv[2])
for name in ('provider.cjs', 'test.cjs'):
    if (workspace / name).read_bytes() != (fixture / name).read_bytes():
        raise SystemExit(f'{name} must remain unchanged')
result = subprocess.run(['node', 'test.cjs'], cwd=workspace, capture_output=True, text=True, timeout=15)
print(result.stdout)
print(result.stderr)
raise SystemExit(result.returncode)
