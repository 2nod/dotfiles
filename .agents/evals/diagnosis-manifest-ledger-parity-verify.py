#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

BUGGY = '''def reconcile(manifest, ledger, receipt=None):
    if receipt and receipt.get("valid"):
        return {"status": "reconciled", "lifecycle": "reconciled"}
    return {"status": "fresh", "lifecycle": manifest["lifecycle"]}
'''


def tests_pass(workspace: pathlib.Path) -> bool:
    return subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(workspace)],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    ).returncode == 0


def probe(workspace: pathlib.Path) -> bool:
    code = """from reconcile import reconcile
mismatch = reconcile({'lifecycle': 'active', 'display_status': '進行中'}, {'lifecycle': 'pr_open', 'display_status': 'PR準備中'})
missing = reconcile({'lifecycle': 'pr_open', 'display_status': 'PR準備中'}, {'lifecycle': 'pr_open', 'display_status': 'PR準備中'})
valid = reconcile({'lifecycle': 'pr_open', 'display_status': 'PR準備中'}, {'lifecycle': 'pr_open', 'display_status': 'PR準備中'}, {'valid': True})
raise SystemExit(0 if mismatch['status'] == 'stale' and missing['status'] == 'stale' and valid['status'] == 'reconciled' else 1)
"""
    return subprocess.run(
        [sys.executable, "-B", "-c", code], cwd=workspace, check=False
    ).returncode == 0


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1]).resolve()
    if not tests_pass(workspace):
        return fail("manifest/ledger regression tests failed")
    if not probe(workspace):
        return fail("reconcile state boundary is incorrect")
    with tempfile.TemporaryDirectory() as temp:
        mutant = pathlib.Path(temp) / "workspace"
        shutil.copytree(workspace, mutant)
        (mutant / "reconcile.py").write_text(BUGGY, encoding="utf-8")
        if tests_pass(mutant):
            return fail("regression tests do not detect mismatch acceptance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
