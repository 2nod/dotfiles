from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

workspace, pristine = map(Path, sys.argv[1:3])
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory)
    shutil.copyfile(pristine / "check_cleanup.py", target / "check_cleanup.py")
    shutil.copyfile(workspace / "cleanup.py", target / "cleanup.py")
    result = subprocess.run([sys.executable, "check_cleanup.py"], cwd=target, capture_output=True, text=True, timeout=8)
    if result.returncode or "Ran 2 tests" not in result.stderr or not result.stderr.rstrip().endswith("OK"):
        print(result.stdout + result.stderr)
        raise SystemExit(1)
print("Every parallel cleanup order is safe; scope and unrelated resources are preserved")
