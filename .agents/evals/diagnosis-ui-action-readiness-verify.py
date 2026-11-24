from pathlib import Path
import subprocess
import sys

workspace, fixture = map(Path, sys.argv[1:3])
test_file = 'test_export_check.py'
if (workspace / test_file).read_bytes() != (fixture / test_file).read_bytes():
    raise SystemExit(f'{test_file} must remain unchanged')

result = subprocess.run(
    ['python3', '-B', test_file], cwd=workspace, capture_output=True, text=True, timeout=5
)
print(result.stdout + result.stderr)
completed = 'Ran 3 tests' in result.stderr and result.stderr.rstrip().endswith('OK')
raise SystemExit(int(result.returncode != 0 or not completed))
