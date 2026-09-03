#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys


FIXTURE_FILES = {"after.py", "before.py", "contract.md"}


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    finding_path = workspace / "findings.md"
    if not finding_path.is_file():
        return fail("findings.md was not created")
    files = {str(path.relative_to(workspace)) for path in workspace.rglob("*") if path.is_file()}
    if files != FIXTURE_FILES | {"findings.md"}:
        return fail("review changed fixture files or created unrelated files")
    finding = finding_path.read_text(encoding="utf-8").lower()
    if "[warning]" not in finding or "after.py" not in finding:
        return fail("collision regression is not reported as a blocking inline finding")
    if "final.json" not in finding or not re.search(r"exist|collision|既存|衝突", finding):
        return fail("finding does not identify the unguarded final writer target")
    if not re.search(r"execute|partial|部分|実行", finding):
        return fail("finding does not explain post-execute partial artifact consumption")
    if not re.search(r"before|pre[- ]?run|pre[- ]?start|前", finding):
        return fail("finding does not place the fix before execution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
