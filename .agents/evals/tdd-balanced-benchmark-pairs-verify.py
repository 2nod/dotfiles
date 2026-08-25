#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


MODE_BLOCKED = '''MODES = ("baseline", "optimized")

def build_schedule(members, key, horizon):
    return [{"mode": mode, "member": member, "latent": latent, "key": key, "horizon": horizon} for mode in MODES for member, latent in members]

def validate_pair(rows):
    return len(rows) == 2
'''


def load(workspace: pathlib.Path):
    spec = importlib.util.spec_from_file_location("scheduler", workspace / "scheduler.py")
    if not spec or not spec.loader:
        raise RuntimeError("could not load scheduler.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tests_pass(workspace: pathlib.Path) -> bool:
    with tempfile.TemporaryDirectory() as cache:
        return subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(workspace)],
            cwd=workspace,
            env={**os.environ, "PYTHONPYCACHEPREFIX": cache},
            capture_output=True,
            text=True,
            check=False,
        ).returncode == 0


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    scheduler = load(workspace)
    members = [(f"member-{index}", (index, index + 1)) for index in range(8)] + [("same-member-control", (0, 1))]
    key = ("evaluation", 41, 0)
    schedule = scheduler.build_schedule(members, key, 144)
    if len(schedule) != 9:
        return fail("schedule is not nine paired tasks")
    orders = set()
    for index, pair in enumerate(schedule):
        if pair.get("pair_index") != index:
            return fail("pair indices are not canonical and contiguous")
        if pair.get("member") != members[index][0] or tuple(pair.get("latent", ())) != members[index][1]:
            return fail("pair member or latent input changed")
        if tuple(pair.get("key", ())) != key or pair.get("horizon") != 144:
            return fail("pair key or horizon changed")
        order = tuple(pair.get("mode_order", ()))
        expected = ("baseline", "optimized") if index % 2 == 0 else ("optimized", "baseline")
        if order != expected:
            return fail("pair mode order is not balanced by canonical index")
        orders.add(order)
        rows = [{"mode": mode} for mode in order]
        if not scheduler.validate_pair(rows):
            return fail("complete pair was rejected")
        for invalid in (rows[:1], [rows[0], rows[0]], [*rows, rows[0]]):
            if scheduler.validate_pair(invalid):
                return fail("duplicate or missing pair mode was accepted")
    if len(orders) != 2 or schedule[8].get("member") != "same-member-control":
        return fail("balanced orders or same-member control are missing")
    if not tests_pass(workspace):
        return fail("regression test suite failed")
    with tempfile.TemporaryDirectory() as temp:
        mutant = pathlib.Path(temp) / "workspace"
        shutil.copytree(workspace, mutant)
        (mutant / "scheduler.py").write_text(MODE_BLOCKED, encoding="utf-8")
        if tests_pass(mutant):
            return fail("regression tests do not detect mode-blocked scheduling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
