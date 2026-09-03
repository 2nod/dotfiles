import json
from pathlib import Path
import subprocess
import sys


workspace = Path(sys.argv[1])
script = workspace / "batch.py"
source = script.read_text(encoding="utf-8")
completed = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=15)
assert completed.returncode == 0, completed.stderr
result = json.loads(completed.stdout)
assert result["mode"] == "fresh_process_per_job_parent_collector"
assert result["workers"] == 4
assert result["values"] == [0, 1, 4, 9]
assert len(set(result["child_pids"])) == 4
assert result["exit_codes"] == [0, 0, 0, 0]
assert result["parent_pid"] not in result["child_pids"]
assert "ThreadPoolExecutor" not in source
assert "threading.Lock" not in source
