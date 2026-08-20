#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

BUGGY = """def parse_count(value: str) -> int:
    try:
        return int(value.strip())
    except ValueError:
        return 0
"""


def tests_pass(workspace: pathlib.Path) -> bool:
    return (
        subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(workspace)],
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def rejects_invalid(workspace: pathlib.Path) -> bool:
    probe = "from parser import parse_count; parse_count('not-a-count')"
    return (
        subprocess.run(
            [sys.executable, "-B", "-c", probe],
            cwd=workspace,
            capture_output=True,
            check=False,
        ).returncode
        != 0
    )


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    if not tests_pass(workspace):
        return fail("regression test suite failed")
    if not rejects_invalid(workspace):
        return fail("malformed input returned a value; expected ValueError")
    with tempfile.TemporaryDirectory() as temp:
        mutant = pathlib.Path(temp) / "workspace"
        shutil.copytree(workspace, mutant)
        (mutant / "parser.py").write_text(BUGGY, encoding="utf-8")
        if tests_pass(mutant):
            return fail("regression tests do not detect the original mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
