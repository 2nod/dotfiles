#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys


FIXTURE_FILES = {"release.py", "test_release.py"}


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
    if "[warning]" not in finding or "test_release.py" not in finding:
        return fail("shared one-shot root is not reported as a blocking finding")
    if not re.search(r"production|shared|live|共有|本番", finding):
        return fail("finding does not identify the shared production root")
    if not re.search(r"consum|pre.?exist|already|used|実行後|使用済", finding):
        return fail("finding does not explain the post-run failure state")
    if not re.search(r"temporarydirectory|temp(file|dir|orary)|一時", finding):
        return fail("finding does not request a fresh temporary root per positive test")
    if not re.search(r"negative|reject|pre.?exist|拒否", finding):
        return fail("finding does not preserve a separate used-root negative case")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
