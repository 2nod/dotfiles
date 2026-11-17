from pathlib import Path
import subprocess
import sys

workspace, fixture = map(Path, sys.argv[1:3])
if (workspace / "test_ledger.py").read_bytes() != (fixture / "test_ledger.py").read_bytes():
    raise SystemExit("test_ledger.py must remain unchanged")
result = subprocess.run([sys.executable, "test_ledger.py"], cwd=workspace, capture_output=True, text=True, timeout=5)
print(result.stdout + result.stderr)
completed = "Ran 5 tests" in result.stderr and result.stderr.rstrip().endswith("OK")
raise SystemExit(int(result.returncode != 0 or not completed))
