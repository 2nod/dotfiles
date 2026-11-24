import json
import runpy
import sys
from pathlib import Path


def check(condition, message):
    if not condition:
        raise SystemExit(message)


def dispatch(path, alias):
    registry = runpy.run_path(str(path))
    return registry["dispatch"](registry["register"](alias))


if sys.argv[1] == "--behavior":
    check(dispatch(Path(sys.argv[2]), "north_2") == "north_2",
          "dispatch failed for a registered alias")
    sys.exit(0)

workspace, fixture = (Path(arg) for arg in sys.argv[1:])
source = fixture / "registry.py"
check((workspace / source.name).read_bytes() == source.read_bytes(), "fixture changed")
check((workspace / "findings.md").read_text().strip(), "review is empty")
evidence = json.loads((workspace / "evidence.json").read_text())
check(evidence["file"] == source.name and evidence["line"] == 13,
      "finding must point to the new parser")
alias = evidence["alias"]
actual = dispatch(source, alias)
check(actual != alias and evidence["expected"] == alias and evidence["actual"] == actual,
      "counterexample must show an accepted alias being misrouted")
