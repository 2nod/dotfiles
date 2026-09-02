#!/usr/bin/env python3
from __future__ import annotations

import html
import pathlib
import re
import sys
from html.parser import HTMLParser


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.pre_blocks: list[list[str]] = []
        self.table_blocks: list[list[str]] = []
        self._pre: list[str] | None = None
        self._table: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "pre":
            self._pre = []
        elif tag == "table":
            self._table = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre" and self._pre is not None:
            self.pre_blocks.append(self._pre)
            self._pre = None
        elif tag == "table" and self._table is not None:
            self.table_blocks.append(self._table)
            self._table = None

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self._pre is not None:
            self._pre.append(data)
        if self._table is not None:
            self._table.append(data)


def fail(message: str) -> int:
    print(message)
    return 1


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def main() -> int:
    workspace = pathlib.Path(sys.argv[1]).resolve()
    report = workspace.parent / "implementation-report" / "index.html"
    if not report.is_file():
        return fail("implementation report is missing outside the product workspace")
    if (workspace / "index.html").exists():
        return fail("implementation report was created inside the product workspace")

    raw = report.read_text(encoding="utf-8")
    parser = ReportParser()
    parser.feed(raw)
    visible = compact(" ".join(parser.text))
    pre_text = [compact(" ".join(block)) for block in parser.pre_blocks]
    table_text = [compact(" ".join(block)) for block in parser.table_blocks]

    code_evidence = (
        "create_job(store, translation_id, request)",
        "lock_translation(translation_id)",
        "current_revision_id != expected_revision_id",
        "target_item is None",
    )
    missing_code = [token for token in code_evidence if not any(token in block for block in pre_text)]
    if missing_code or len(pre_text) < 4 or "Before" not in visible or "After" not in visible:
        return fail(f"report is missing reviewable code Before / After evidence: {missing_code}")

    contract_tokens = ("resultArtifact", "targetItem", "fr-FR", "fr", "zh-TW")
    if not any(all(token in table for token in contract_tokens) for table in table_text):
        return fail("field, locale alias, and unsupported value must remain together in a contract table")

    invariant_ids = (
        "INV-MOVED-ITEM",
        "INV-REPLAY-REPAIR",
        "INV-EXACT-OUTPUT",
        "INV-REVISION-CAS",
    )
    missing_invariants = [token for token in invariant_ids if token not in visible]
    if missing_invariants:
        return fail(f"report is missing safety invariants: {missing_invariants}")

    if "12 / 12" not in visible or "9 / 9" in visible:
        return fail("report must use current verification and remove the superseded count")

    ids = re.findall(r'\bid=["\']([^"\']+)["\']', raw)
    if len(ids) != len(set(ids)):
        return fail("implementation report contains duplicate IDs")
    hrefs = re.findall(r'\bhref=["\']#([^"\']+)["\']', raw)
    if not hrefs or any(target not in ids for target in hrefs):
        return fail("implementation report contains a broken or missing internal link")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
