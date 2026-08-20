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
    report_path = workspace / "daily-triage.json"
    if not report_path.is_file():
        return fail("daily-triage.json was not created")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return fail(f"daily-triage.json is invalid: {error}")

    expected = {
        "candidate_source": "pinned",
        "doing": ["Implement billing export"],
        "pending": ["Choose analytics vendor"],
        "completion_candidates": ["Retire legacy flag"],
        "excluded_unpinned": ["Investigate flaky test"],
    }
    if report != expected:
        return fail(f"unexpected daily triage: {report!r}")

    fixture_path = workspace / "codex-tasks.json"
    expected_fixture = json.loads(
        pathlib.Path(__file__)
        .with_name("fixtures")
        .joinpath("daily-task-triage-pinned-status", "codex-tasks.json")
        .read_text(encoding="utf-8")
    )
    if json.loads(fixture_path.read_text(encoding="utf-8")) != expected_fixture:
        return fail("codex-tasks.json was modified")

    expected_names = {"codex-tasks.json", "daily-triage.json"}
    actual_names = {path.name for path in workspace.iterdir()}
    if actual_names != expected_names:
        return fail(f"fixture files were added or removed: {actual_names!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
