#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys


FIXTURE_FILES = {"provenance.py", "test_provenance.py"}


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    finding_path = workspace / "findings.md"
    if not finding_path.is_file():
        return fail("findings.md was not created")

    files = {
        str(path.relative_to(workspace))
        for path in workspace.rglob("*")
        if path.is_file()
    }
    if files != FIXTURE_FILES | {"findings.md"}:
        return fail("review changed fixture files or created unrelated files")

    finding = finding_path.read_text(encoding="utf-8").lower()
    if "[warning]" not in finding or "test_provenance.py" not in finding:
        return fail("fixture inconsistency is not reported as a blocking finding")
    if not re.search(r"100\s*[/,:]\s*90|100.*90", finding):
        return fail("finding does not identify the visible branch money")
    if not re.search(r"margin.{0,40}10|10.{0,40}margin", finding):
        return fail("finding does not derive the branch margin of 10")
    if not re.search(r"12", finding):
        return fail("finding does not identify the inconsistent stored margin of 12")
    if not re.search(r"same|equal|both|両|同量", finding) or not re.search(r"shift|offset|改ざん|ずら", finding):
        return fail("finding does not request an equal-shift tamper case")
    if not re.search(r"nan|infinity|non[- ]?finite|非有限", finding):
        return fail("finding does not request non-finite margin coverage")
    if not re.search(r"derive|recompute|source|state|導出|再計算|正本", finding):
        return fail("finding does not reconnect expected margins to branch state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
