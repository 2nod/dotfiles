#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys


CORRECT = "1a086a460d0c23030ac0f0f451683ed672088d30"
WRONG = "1a086a4f3af1bc75fec390ba6220a524628f325c"
CURRENT = "309d3b58246899416ff27bd58710ae1c2a7e001e"


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    source_path = workspace / "pr-metadata.json"
    output_path = workspace / "corrected-pr-metadata.json"
    expected_source = {
        "pr": {"number": 256, "url": "https://example.invalid/pull/256"},
        "short_oid": "1a086a4",
        "creation_head": WRONG,
        "implementation_head": WRONG,
        "current_pr_head": CURRENT,
        "commit_objects": [CORRECT, CURRENT],
        "handoff_entry_count": 1,
    }
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return fail(f"pr-metadata.json is invalid: {error}")
    if source != expected_source:
        return fail("pr-metadata.json was modified")
    if not output_path.is_file():
        return fail("corrected-pr-metadata.json was not created")
    try:
        output = json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return fail(f"corrected-pr-metadata.json is invalid: {error}")
    expected_output = {
        "pr": expected_source["pr"],
        "creation_head": CORRECT,
        "implementation_head": CORRECT,
        "correction": "metadata_factual_correction",
        "evidence": "existing_commit_object_unique_short_oid_match",
        "handoff_entry_count": 1,
        "prohibited_actions": ["force_push", "rebase", "additional_handoff", "record_current_pr_head"],
    }
    if output != expected_output:
        return fail(f"unexpected corrected metadata: {output!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
