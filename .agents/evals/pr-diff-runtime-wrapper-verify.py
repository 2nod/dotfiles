#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys


FIXTURE_FILES = {
    "after.nix",
    "before.nix",
    "dispatcher.sh",
    "environment.md",
}


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
    if "[warning]" not in finding or "after.nix" not in finding:
        return fail("runtime regression is not reported as a blocking inline finding")
    if "node" not in finding or "path" not in finding:
        return fail("finding does not identify the missing runtime dependency")
    if not re.search(
        r"non[- ]?interactive|automation|service|shell initialization|非対話|自動化|サービス|shell 初期化",
        finding,
    ):
        return fail("finding does not state the environment that triggers the regression")
    if not re.search(r"not found|fails?|failure|見つから|失敗", finding):
        return fail("finding does not explain the dispatcher failure")
    if not re.search(r"wrapper|wrap|ラッパー", finding):
        return fail("finding does not recommend retaining a runtime wrapper")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
