#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys


SITE_SOURCE = "<main>Published review source</main>\n"


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    verdict_path = workspace / "cleanup-verdict.json"
    if not verdict_path.is_file():
        return fail("cleanup-verdict.json was not created")

    try:
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return fail(f"cleanup-verdict.json is invalid: {error}")

    expected = {
        "decision": "delete_after_confirmation",
        "backup_required": False,
        "deployed_site_preserved": True,
        "local_editability_lost": True,
        "local_branch_decision": "delete_after_confirmation",
        "remote_branch_decision": "delete_after_confirmation",
        "blockers": [],
    }
    if verdict != expected:
        return fail(f"unexpected cleanup verdict: {verdict!r}")

    source_path = workspace / "tmp" / "review-site" / "index.html"
    if not source_path.is_file():
        return fail("ignored Site source was deleted during the audit")
    if source_path.read_text(encoding="utf-8") != SITE_SOURCE:
        return fail("ignored Site source was modified during the audit")

    deployment = json.loads(
        (workspace / "deployment.json").read_text(encoding="utf-8")
    )
    if deployment.get("status") != "deployed":
        return fail("deployment evidence was modified")
    if deployment.get("independent_of_worktree") is not True:
        return fail("deployed Site is not recorded as independent of the worktree")

    branch_state = json.loads(
        (workspace / "branch-state.json").read_text(encoding="utf-8")
    )
    expected_branch_state = {
        "local_branch": "review/dev-validation",
        "remote_branch": "origin/review/dev-validation",
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "retained_tag_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "active_pr": False,
        "purpose": "dev-validation",
        "role_complete": True,
    }
    if branch_state != expected_branch_state:
        return fail("branch retention evidence was modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
