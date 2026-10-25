"""Legacy test: verifies only the handler, bypassing registration."""
from pathlib import Path
import subprocess
import sys
assert "[dispatch]" in subprocess.check_output(
    [sys.executable, str(Path(__file__).parent / "extension/handler.py")], text=True,
)
print("handler passes")
