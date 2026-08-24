#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    body_path = workspace / "pr-body.md"
    if not body_path.is_file():
        return fail("pr-body.md was not created")

    body = body_path.read_text(encoding="utf-8")
    headings = ["## 背景と課題", "## 実装詳細と変更点", "## 確認項目"]
    positions = [body.find(heading) for heading in headings]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        return fail("required PR sections are missing or out of order")

    required_facts = (
        "event_id",
        "channel",
        "idempotency key",
        "再試行",
        "email",
        "webhook",
        "npm test -- notification-idempotency.test.ts",
        "18 passed",
        "保持期間",
    )
    if not all(fact in body for fact in required_facts):
        return fail("the final contract, verification, or scope boundary is incomplete")

    chronology_markers = (
        "前回",
        "追加対応",
        "追加で",
        "訂正",
        "先ほど",
        "経緯",
        "当初",
        "最初は",
        "レビューで",
    )
    if any(marker in body for marker in chronology_markers):
        return fail("conversation or revision chronology remains in the PR description")

    obsolete_claims = (
        r"job_id\s*を\s*idempotency key\s*に(?:する|した)",
        r"job_id\s*だけ",
        r"job_id\s*単体",
    )
    if any(re.search(pattern, body) for pattern in obsolete_claims):
        return fail("the obsolete job_id-only design is presented as current")
    if "<!--" in body:
        return fail("template comments remain in the submitted body")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
