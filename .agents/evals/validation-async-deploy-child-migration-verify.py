#!/usr/bin/env python3
"""Verify that a green parent does not hide a failing asynchronous migration."""

import json
from pathlib import Path
import sys


def main() -> int:
    workspace = Path(sys.argv[1])
    original = Path(sys.argv[2])
    for name in ("parent_run.json", "migration_task.json"):
        if (workspace / name).read_bytes() != (original / name).read_bytes():
            return 1

    try:
        result = json.loads((workspace / "result.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return 1

    expected = {
        "overall_status": "incomplete",
        "parent_status": "success",
        "migration_status": "retrying",
        "evidence": {
            "parent_run_id": "run-42",
            "migration_task_id": "task-7",
            "latest_http_status": 500,
        },
        "next_action": "investigate_child_failure",
    }
    return 0 if result == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
