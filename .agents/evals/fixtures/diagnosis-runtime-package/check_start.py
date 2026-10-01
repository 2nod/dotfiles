"""Exercise startup, not just the version flag, using synthetic executables."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from bundle import package


RUNTIME = '''import json
from pathlib import Path
import sys

if sys.argv[1:] == ["--version"]:
    print("runner 2.3.4")
    raise SystemExit(0)
root = Path(__file__).resolve().parent.parent
try:
    manifest = json.loads((root / "runtime.json").read_text())
    assert manifest == {"version": "2.3.4", "entrypoint": "bin/runner"}
    assert (root / "bin/worker").read_bytes() == b"synthetic worker"
    assert (root / "tools/search").read_bytes() == b"synthetic search"
    assert all(not p.is_symlink() for p in root.rglob("*"))
except (OSError, ValueError, AssertionError):
    sys.exit("incomplete runtime package")
print("daemon ready")
'''


def check():
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        source, destination = base / "compiler", base / "release"
        (source / "bin").mkdir(parents=True)
        (source / "tools").mkdir()
        (source / "bin/runner").write_text(RUNTIME)
        (source / "bin/runner").chmod(0o755)
        (source / "bin/worker").write_bytes(b"synthetic worker")
        (source / "tools/search").write_bytes(b"synthetic search")
        (source / "runtime.json").write_text(json.dumps({
            "version": "2.3.4", "entrypoint": "bin/runner",
        }))
        package(source, destination)
        entry = destination / "bin/runner"
        command = [sys.executable, str(entry)]
        version = subprocess.run(command + ["--version"], capture_output=True, text=True)
        assert version.returncode == 0 and version.stdout.strip() == "runner 2.3.4"
        # The deploy must survive removal of the compiler output. In particular,
        # an executable symlink would resolve the package root to the wrong tree.
        source.rename(base / "retired-compiler")
        started = subprocess.run(command + ["daemon-start"], capture_output=True, text=True)
        assert started.returncode == 0, started.stderr
        assert started.stdout.strip() == "daemon ready", started.stdout
        assert entry.stat().st_mode & 0o111, "entrypoint lost its executable mode"
        print("PASS: version and daemon startup from an independent release")


if __name__ == "__main__":
    check()
