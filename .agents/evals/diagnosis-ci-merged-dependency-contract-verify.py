from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

workspace, pristine = map(Path, sys.argv[1:3])
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory)
    for name in ["schema_api.py", "ci.json", "check_events.py"]:
        shutil.copyfile(pristine / name, target / name)
    shutil.copyfile(workspace / "events.py", target / "events.py")
    for options in [[], ["--ci"]]:
        result = subprocess.run([sys.executable, "check_events.py", *options], cwd=target, capture_output=True, text=True, timeout=8)
        completed = "Ran 4 tests" in result.stderr and result.stderr.rstrip().endswith("OK")
        if result.returncode or not completed:
            print(result.stdout + result.stderr)
            raise SystemExit(1)
print("Local and merged dependency contracts pass")
