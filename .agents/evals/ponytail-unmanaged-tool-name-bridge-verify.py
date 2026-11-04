from pathlib import Path
import subprocess
import sys

workspace, fixture = map(Path, sys.argv[1:3])
assert (workspace / "upstream.py").read_bytes() == (fixture / "upstream.py").read_bytes(), "Do not change the unmanaged provider"
result = subprocess.run([sys.executable, "-B", "-c", (fixture / "test_bridge.py").read_text()], cwd=workspace, capture_output=True, text=True, timeout=5)
print(result.stdout + result.stderr)
completed = "Consumer naming, original dispatch and result preservation passed" in result.stdout
raise SystemExit(int(result.returncode != 0 or not completed))
