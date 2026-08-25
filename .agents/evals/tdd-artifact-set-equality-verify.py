#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


BUGGY = '''import hashlib
import json


def _fingerprint(values):
    payload = json.dumps(sorted(set(values)), separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def audit(generated, reference, expected_count):
    generated_set = set(generated)
    return {
        "success": len(generated_set) == expected_count,
        "missing": max(0, expected_count - len(generated_set)),
        "generated_set_sha256": _fingerprint(generated_set),
    }
'''


def tests_pass(workspace: pathlib.Path) -> bool:
    with tempfile.TemporaryDirectory() as cache:
        return subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(workspace)],
            env={**os.environ, "PYTHONPYCACHEPREFIX": cache},
            capture_output=True,
            text=True,
            check=False,
        ).returncode == 0


def fail(message: str) -> int:
    print(message)
    return 1


def load_module(workspace: pathlib.Path):
    spec = importlib.util.spec_from_file_location("artifact", workspace / "artifact.py")
    if not spec or not spec.loader:
        raise RuntimeError("could not load artifact.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    module = load_module(workspace)

    substituted = module.audit(["a", "x"], ["a", "b"], 2)
    if substituted.get("success"):
        return fail("same-count substitution was accepted")
    if substituted.get("missing") != ["b"]:
        return fail(f"missing IDs are wrong: {substituted.get('missing')!r}")
    if substituted.get("unexpected") != ["x"]:
        return fail(f"unexpected IDs are wrong: {substituted.get('unexpected')!r}")
    if substituted.get("generated_set_sha256") == substituted.get("reference_set_sha256"):
        return fail("different sets have the same reported fingerprint")

    mismatch = module.audit(["a", "b"], ["a", "b"], 3)
    if mismatch.get("success"):
        return fail("reference count mismatch was accepted")

    exact = module.audit(["b", "a"], ["a", "b"], 2)
    if not exact.get("success") or exact.get("missing") or exact.get("unexpected"):
        return fail(f"exact set match was rejected: {exact!r}")
    if exact.get("generated_set_sha256") != exact.get("reference_set_sha256"):
        return fail("equal sets have different reported fingerprints")
    if not tests_pass(workspace):
        return fail("regression test suite failed")

    with tempfile.TemporaryDirectory() as temp:
        mutant = pathlib.Path(temp) / "workspace"
        shutil.copytree(workspace, mutant)
        (mutant / "artifact.py").write_text(BUGGY, encoding="utf-8")
        if tests_pass(mutant):
            return fail("regression tests do not detect the count-only implementation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
