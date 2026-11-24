import json
import runpy
import sys
from pathlib import Path


def check(condition, message):
    if not condition:
        raise SystemExit(message)


def missing_labels(path):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(path.parent))
    return runpy.run_path(str(path))["missing_labels"]


if sys.argv[1] == "--behavior":
    report = missing_labels(Path(sys.argv[2]).resolve())
    check(report(["a", "b", "c"], {"a": "ok", "b": ""}) == ["b", "c"],
          "report dropped an active item with no index entry")
    sys.exit(0)

workspace, fixture = (Path(arg).resolve() for arg in sys.argv[1:])
for source in fixture.iterdir():
    check((workspace / source.name).read_bytes() == source.read_bytes(),
          f"review modified {source.name}")
check((workspace / "findings.md").read_text().strip(), "review is empty")
evidence = json.loads((workspace / "evidence.json").read_text())
check(evidence["file"] == "after.py" and evidence["line"] == 6,
      "finding must point at the changed enumeration")
catalog, indexed = evidence["catalog"], evidence["indexed"]
check(isinstance(catalog, list) and isinstance(indexed, dict), "invalid report inputs")
expected = missing_labels(fixture / "before.py")(catalog, indexed)
actual = missing_labels(fixture / "after.py")(catalog, indexed)
check(expected != actual and evidence["expected"] == expected and evidence["actual"] == actual,
      "counterexample does not distinguish the candidate from the contract-preserving version")
