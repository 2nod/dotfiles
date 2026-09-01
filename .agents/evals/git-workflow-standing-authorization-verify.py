#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys


def fail(message: str) -> int:
    print(message)
    return 1


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    decisions_path = workspace / "authority-decisions.json"
    expected_inputs = {
        "project-authority.md": "64c55cb5f487640b434d0cb7e1755b324b47073ae83f290b7e181f63a55eacdd",
        "operation-cases.json": "584be8e1a4625df6d2c4a54bfa6b4e5acd4af31cf3921010e3bbc6dd57532ec7",
    }
    for relative_path, expected_hash in expected_inputs.items():
        path = workspace / relative_path
        if not path.is_file() or sha256(path) != expected_hash:
            return fail(f"{relative_path} was modified")

    if not decisions_path.is_file():
        return fail("authority-decisions.json was not created")

    try:
        decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return fail(f"authority-decisions.json is invalid: {error}")

    expected = [
        {
            "id": "private-origin-task-flow",
            "decision": "allow",
            "reason": "all_constraints_pass",
        },
        {
            "id": "direct-main-push",
            "decision": "deny",
            "reason": "task_branch",
        },
        {
            "id": "public-origin",
            "decision": "deny",
            "reason": "remote_visibility",
        },
        {
            "id": "force-push",
            "decision": "deny",
            "reason": "force_push",
        },
        {
            "id": "rebase-request",
            "decision": "deny",
            "reason": "rebase",
        },
        {
            "id": "mixed-task-stage",
            "decision": "deny",
            "reason": "staged_paths",
        },
        {
            "id": "validator-unknown",
            "decision": "deny",
            "reason": "dedicated_worktree",
        },
        {
            "id": "delegation-only",
            "decision": "deny",
            "reason": "no_standing_authorization",
        },
    ]
    if decisions != expected:
        return fail(f"unexpected authority decisions: {decisions!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
