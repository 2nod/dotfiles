#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import subprocess
import sys


def run(workspace: pathlib.Path, *args: str) -> bool:
    return subprocess.run(
        [sys.executable, "-B", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    ).returncode == 0


def main() -> int:
    workspace = pathlib.Path(sys.argv[1]).resolve()
    if not run(workspace, "-m", "unittest", "discover", "-s", str(workspace)):
        print("public shared-projection regression test failed")
        return 1
    probe = """from collector import collect_prefix
from test_collector import SharedRawEngine
seen = {0: [], 1: []}
def controller(obs):
    seen[obs['player']].append((obs['step'], obs['private']))
engine = SharedRawEngine()
collect_prefix(engine, [controller, controller], steps=2)
raise SystemExit(0 if seen == {0: [(0, 'left'), (1, 'left')], 1: [(0, 'right'), (1, 'right')]} else 1)
"""
    if not run(workspace, "-c", probe):
        print("agent-visible shared projection or private boundary is incorrect")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
