import importlib
import subprocess
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if len(sys.argv) == 2:
    result = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), sys.argv[1], "--check"],
        capture_output=True, text=True, timeout=5,
    )
    print(result.stdout + result.stderr)
    completed = "PASS strict public boundaries and deliberately permissive route" in result.stdout
    raise SystemExit(int(result.returncode != 0 or not completed))

workspace = Path(sys.argv[1]).resolve()
expected_framework = Path(__file__).parent / "fixtures" / "ponytail-strict-adapter-boundary" / "framework.py"
assert (workspace / "framework.py").read_bytes() == expected_framework.read_bytes(), "Do not change framework policy"
sys.path.insert(0, str(workspace))
service = importlib.import_module("service")
for name, payload in [("label", {"title": "Sample"}), ("quantity", {"units": 4})]:
    assert service.request(name, payload) == {"ok": True, "value": payload}
    count = service.calls[name]
    for extra in ["spare", "memo", "mode"]:
        result = service.request(name, {**payload, extra: "unused"})
        assert result == {"ok": False}, f"Public {name} accepted extra key {extra}"
        assert service.calls[name] == count, "Invalid requests reached the handler"
    assert service.request(name, {}) == {"ok": False}
assert service.request("open", {"note": "Allowed", "spare": "ignored"}) == {"ok": True, "value": {"note": "Allowed"}}
print("PASS strict public boundaries and deliberately permissive route")
