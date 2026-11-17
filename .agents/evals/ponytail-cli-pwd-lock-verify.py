from pathlib import Path
import subprocess
import sys

workspace, fixture = map(Path, sys.argv[1:3])
for name in ["resource_cli.py", "test_deploy.py"]:
    assert (workspace / name).read_bytes() == (fixture / name).read_bytes(), "Only deploy.py may change"
result = subprocess.run([sys.executable, "-B", "test_deploy.py"], cwd=workspace, capture_output=True, text=True, timeout=5)
print(result.stdout + result.stderr)
completed = 'Package-relative identity and inherited environment preserved' in result.stdout
raise SystemExit(int(result.returncode != 0 or not completed))
