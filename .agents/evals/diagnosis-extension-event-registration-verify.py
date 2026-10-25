from pathlib import Path
import subprocess
import sys
workspace, original = map(Path, sys.argv[1:3])
for filename in ["platform_runtime.py", "extension/handler.py"]:
    assert (workspace / filename).read_bytes() == (original / filename).read_bytes(), filename + " must remain unchanged"
result = subprocess.run([sys.executable, "-B", "-c", (original / "check_registration.py").read_text().replace("Path(__file__).resolve().parent", "Path.cwd()")], cwd=workspace, capture_output=True, text=True, timeout=5)
print(result.stdout + result.stderr)
raise SystemExit(int(result.returncode != 0))
