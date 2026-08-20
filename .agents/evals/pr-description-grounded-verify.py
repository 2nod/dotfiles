#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys


def fail(message: str) -> int:
    print(message)
    return 1


def section(text: str, heading: str, next_heading: str = "") -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    if not next_heading:
        return text[start:]
    end = text.find(next_heading, start)
    return text[start:] if end < 0 else text[start:end]


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    body_path = workspace / "pr-body.md"
    if not body_path.is_file():
        return fail("pr-body.md was not created")

    body = body_path.read_text(encoding="utf-8")
    headings = [
        "## 背景と課題",
        "## 実装詳細と変更点",
        "## 確認項目",
        "## その他の備考",
    ]
    positions = [body.find(heading) for heading in headings]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        return fail("required PR sections are missing or out of order")

    background = section(body, headings[0], headings[1])
    if not all(token in background for token in ("archived", "監査担当者", "手作業")):
        return fail("background does not explain the current behavior and user impact")

    implementation = section(body, headings[1], headings[2])
    required_design_facts = (
        "ExportSelection",
        "selected_ids",
        "未選択",
        "すべて",
        "export範囲",
    )
    if not all(token in implementation for token in required_design_facts):
        return fail("design choice or rejected-option tradeoff is incomplete")

    checks = section(body, headings[2], headings[3])
    required_checks = (
        "明示選択",
        "未選択",
        "active",
        "npm test -- export-selection.test.ts",
        "12 passed",
    )
    if not all(token in checks for token in required_checks):
        return fail("QA behavior or development evidence is incomplete")
    if checks.count("- [x]") < 4:
        return fail("confirmed QA and development checks are not marked as completed")

    notes = section(body, headings[3])
    if not all(token in notes for token in ("スコープ外", "すべて")):
        return fail("out-of-scope behavior is not explicit")

    if re.search(r"https?://", body):
        return fail("a related link was invented")
    if "path/to/file" in body or "<details>" in body:
        return fail("an empty or invented changed-file block remains")
    if "<!--" in body:
        return fail("template comments remain in the submitted body")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
