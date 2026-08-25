#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile


BUGGY = '''def labels_for_observations(steps):
    """Return the current and following actions for each observation.

    An action stored on step N was selected from the observation on step N - 1.
    """
    rows = []
    for index, step in enumerate(steps):
        rows.append(
            {
                "observation": step["observation"],
                "action_t0": step.get("action"),
                "action_t1": steps[index + 1].get("action") if index + 1 < len(steps) else None,
            }
        )
    return rows
'''


def tests_pass(workspace: pathlib.Path) -> bool:
    return (
        subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(workspace)],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def alignment_is_correct(workspace: pathlib.Path) -> bool:
    probe = """from event_alignment import labels_for_observations
steps = [
    {"observation": "o0", "action": None},
    {"observation": "o1", "action": "a0"},
    {"observation": "o2", "action": "a1"},
]
row = labels_for_observations(steps)[0]
raise SystemExit(0 if row["action_t0"] == "a0" and row["action_t1"] == "a1" else 1)
"""
    return (
        subprocess.run(
            [sys.executable, "-B", "-c", probe],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1]).resolve()
    if not tests_pass(workspace):
        return fail("regression test suite failed")
    if not alignment_is_correct(workspace):
        return fail("observation/action alignment is still shifted")
    test_text = (workspace / "test_event_alignment.py").read_text(encoding="utf-8")
    if "action_t0" not in test_text or "action_t1" not in test_text:
        return fail("missing regression assertions for both aligned labels")
    with tempfile.TemporaryDirectory() as temp:
        mutant = pathlib.Path(temp) / "workspace"
        shutil.copytree(workspace, mutant)
        (mutant / "event_alignment.py").write_text(BUGGY, encoding="utf-8")
        if tests_pass(mutant):
            return fail("regression tests do not detect the original mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
