#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    report_path = workspace / "cleanup-report.json"
    if not report_path.is_file():
        return fail("cleanup-report.json was not created")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return fail(f"cleanup-report.json is invalid: {error}")

    expected_worktrees = [
        {
            "path": "/workspace/.codex/worktrees/alpha/project",
            "codex_task_title": "Alpha validation",
            "codex_task_status": "idle",
            "pinned": True,
            "archived": False,
        },
        {
            "path": "/workspace/.codex/worktrees/beta/project",
            "codex_task_title": "Beta implementation",
            "codex_task_status": "active",
            "pinned": False,
            "archived": False,
        },
    ]
    if report.get("worktrees") != expected_worktrees:
        return fail(f"unexpected worktree task mapping: {report.get('worktrees')!r}")
    if report.get("archive_candidates") != ["Removed experiment"]:
        return fail(f"unexpected archive candidates: {report.get('archive_candidates')!r}")

    expected_worktree_fixture = [
        {
            "path": "/workspace/.codex/worktrees/alpha/project",
            "branch": "feature/alpha",
            "dirty": 0,
        },
        {
            "path": "/workspace/.codex/worktrees/beta/project",
            "branch": "feature/beta",
            "dirty": 2,
        },
    ]
    expected_task_fixture = [
        {
            "cwd": "/workspace/.codex/worktrees/alpha/project",
            "title": "Alpha validation",
            "status": "idle",
            "pinned": True,
            "archived": False,
        },
        {
            "cwd": "/workspace/.codex/worktrees/beta/project",
            "title": "Beta implementation",
            "status": "active",
            "pinned": False,
            "archived": False,
        },
        {
            "cwd": "/workspace/.codex/worktrees/removed/project",
            "title": "Removed experiment",
            "status": "notLoaded",
            "pinned": False,
            "archived": False,
        },
    ]
    actual_worktree_fixture = json.loads(
        (workspace / "worktrees.json").read_text(encoding="utf-8")
    )
    if actual_worktree_fixture != expected_worktree_fixture:
        return fail("worktrees.json was modified")
    actual_task_fixture = json.loads(
        (workspace / "codex-tasks.json").read_text(encoding="utf-8")
    )
    if actual_task_fixture != expected_task_fixture:
        return fail("codex-tasks.json was modified")

    expected_fixture_names = {
        "worktrees.json",
        "codex-tasks.json",
        "cleanup-report.json",
    }
    actual_fixture_names = {path.name for path in workspace.iterdir()}
    if actual_fixture_names != expected_fixture_names:
        return fail(f"fixture files were added or removed: {actual_fixture_names!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
