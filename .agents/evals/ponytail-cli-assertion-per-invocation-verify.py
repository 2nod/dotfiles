import pathlib
import subprocess
import sys
workspace, fixture = map(pathlib.Path, sys.argv[1:])
for name in ('provider.cjs', 'release.cjs', 'test.cjs'):
    if (workspace / name).read_bytes() != (fixture / name).read_bytes():
        raise SystemExit(f'{name} must remain unchanged')
result = subprocess.run(['node', 'test.cjs'], cwd=workspace, capture_output=True, text=True, timeout=10)
print(result.stdout)
print(result.stderr)
completed = 'Every CLI invocation refreshes, including cleanup; refresh failure prevents invocation' in result.stdout
raise SystemExit(int(result.returncode != 0 or not completed))
