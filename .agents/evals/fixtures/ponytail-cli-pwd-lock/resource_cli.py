import json
import os
from pathlib import Path

assert os.environ["SYNTHETIC_SETTING"] == "keep-me"
lock_path = Path("resource-lock.json")
lock = json.loads(lock_path.read_text())
key = "./" + os.path.relpath(Path.cwd() / "units/example", os.environ["PWD"])
if key not in lock:
    lock[key] = "resource_duplicate"
lock_path.write_text(json.dumps(lock))
