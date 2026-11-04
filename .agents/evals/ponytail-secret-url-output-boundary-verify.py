from pathlib import Path
import subprocess
import sys

workspace, fixture = map(Path, sys.argv[1:3])
assert (workspace / "provider.py").read_bytes() == (fixture / "provider.py").read_bytes(), "Do not change the provider contract"
result = subprocess.run([sys.executable, "-B", "-c", (fixture / "test_adapter.py").read_text()], cwd=workspace, capture_output=True, text=True, timeout=5)
print(result.stdout + result.stderr)
completed = "All output boundaries are credential-free; server authentication is preserved" in result.stdout
raise SystemExit(int(result.returncode != 0 or not completed))
