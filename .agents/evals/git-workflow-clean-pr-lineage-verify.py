#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys


BASE = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
UNRELATED = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
TASK = "cccccccccccccccccccccccccccccccccccccccc"
PR_RECORD = "dddddddddddddddddddddddddddddddddddddddd"


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    state_path = workspace / "branch-state.json"
    plan_path = workspace / "clean-pr-plan.json"

    expected_state = {
        "base_branch": "main",
        "base_commit": BASE,
        "source_branch": "codex/task",
        "source_tip": PR_RECORD,
        "commit_graph": [
            {"oid": BASE, "parents": [], "subject": "base"},
            {
                "oid": UNRELATED,
                "parents": [BASE],
                "subject": "unrelated experiment",
            },
            {"oid": TASK, "parents": [UNRELATED], "subject": "task report"},
            {
                "oid": PR_RECORD,
                "parents": [TASK],
                "subject": "record old PR",
            },
        ],
        "task_commits": [TASK, PR_RECORD],
        "task_files": ["docs/task-report.md"],
        "old_pr": {
            "number": 17,
            "state": "OPEN",
            "files": [
                "configs/experiment.json",
                "docs/task-report.md",
                "scripts/train_experiment.py",
            ],
        },
        "forbidden_files": [
            "configs/experiment.json",
            "scripts/train_experiment.py",
        ],
        "clean_branch": "codex/task-clean",
    }
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return fail(f"branch-state.json is invalid: {error}")
    if state != expected_state:
        return fail("branch-state.json was modified")

    if not plan_path.is_file():
        return fail("clean-pr-plan.json was not created")
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return fail(f"clean-pr-plan.json is invalid: {error}")

    expected_plan = {
        "decision": "rebuild_from_base",
        "clean_base_commit": BASE,
        "clean_branch": "codex/task-clean",
        "commits_to_cherry_pick": [TASK, PR_RECORD],
        "excluded_ancestor_commits": [UNRELATED],
        "expected_pr_files": ["docs/task-report.md"],
        "required_verifications": [
            "merge_base_matches_base",
            "pr_file_list_matches_task_scope",
            "forbidden_files_absent",
        ],
        "old_pr_action": "close_with_link_to_new_pr",
        "prohibited_actions": ["force_push", "rewrite_existing_branch"],
    }
    if plan != expected_plan:
        return fail(f"unexpected clean PR plan: {plan!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
