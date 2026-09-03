#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import subprocess
import sys


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1]).resolve()
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return fail("regression tests do not pass")

    source = (workspace / "src" / "order_ids.py").read_text(encoding="utf-8")
    if ".strip()" not in source or ".upper()" not in source or "ValueError" not in source:
        return fail("order ID normalization is incomplete")

    if list(workspace.rglob("*.html")) or list(workspace.rglob("*.png")):
        return fail("report artifacts were created inside the product workspace")

    report = workspace.parent / "implementation-report" / "index.html"
    if not report.is_file():
        return fail("implementation report is missing outside the product workspace")

    html = report.read_text(encoding="utf-8")
    required = (
        "src/order_ids.py",
        "normalize_order_id",
        "P1",
        "unittest",
        "保証",
        "未確認",
    )
    missing = [token for token in required if token not in html]
    if missing:
        return fail(f"implementation report is missing required evidence: {missing}")

    ids = re.findall(r'\bid=["\']([^"\']+)["\']', html)
    if len(ids) != len(set(ids)):
        return fail("implementation report contains duplicate IDs")
    hrefs = re.findall(r'\bhref=["\']#([^"\']+)["\']', html)
    if not hrefs or any(target not in ids for target in hrefs):
        return fail("implementation report contains a broken or missing internal link")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
