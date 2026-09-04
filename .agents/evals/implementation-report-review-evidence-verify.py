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
        self.aside_blocks: list[list[str]] = []
        self.aside_hrefs: list[str] = []
        self._pre: list[str] | None = None
        self._table: list[str] | None = None
        self._aside: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "pre":
            self._pre = []
        elif tag == "table":
            self._table = []
        elif tag == "aside":
            self._aside = []
        elif tag == "a" and self._aside is not None:
            href = dict(attrs).get("href")
            if href and href.startswith("#"):
                self.aside_hrefs.append(href[1:])

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre" and self._pre is not None:
            self.pre_blocks.append(self._pre)
            self._pre = None
        elif tag == "table" and self._table is not None:
            self.table_blocks.append(self._table)
            self._table = None
        elif tag == "aside" and self._aside is not None:
            self.aside_blocks.append(self._aside)
            self._aside = None

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self._pre is not None:
            self._pre.append(data)
        if self._table is not None:
            self._table.append(data)
        if self._aside is not None:
            self._aside.append(data)


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
    if "入力" not in visible:
        return fail("change units must describe their inputs")
    if max(visible.index(token) for token in invariant_ids) > visible.index("入力"):
        return fail("cross-cutting invariants must appear before the change-unit details")

    unit_order = ("役割", "目的", "入力", "判定・防御", "出力", "Before / After", "テスト証拠")
    cursor = 0
    for _ in range(2):
        for token in unit_order:
            position = visible.find(token, cursor)
            if position < 0:
                return fail(f"two change units must use the same evidence order: missing {token}")
            cursor = position + len(token)

    if not parser.aside_blocks or len(set(parser.aside_hrefs)) < 2:
        return fail("a right-side change-unit navigation with at least two anchors is required")
    aside = compact(" ".join(parser.aside_blocks[0]))
    status_tokens = ("実装", "自動テスト", "ローカルE2E", "未確認")
    missing_status = [token for token in status_tokens if token not in aside]
    if missing_status:
        return fail(f"navigation must separate implementation and verification status: {missing_status}")

    test_evidence = ("検証意図", "前提（Arrange）", "共通の操作（Act）", "期待結果（Assert）", "tests/test_job_flow.py")
    missing_test_evidence = [token for token in test_evidence if token not in visible]
    if missing_test_evidence:
        return fail(f"test evidence must use AAA and an actual file path: {missing_test_evidence}")
    if visible.count("共通の操作（Act）") != 2:
        return fail("each of the two change units must state its shared Act exactly once")
    if visible.count("検証意図") < 3:
        return fail("a case-specific verification intent is required for each of the three test cases")
    if visible.count("前提（Arrange）") < 3 or visible.count("期待結果（Assert）") < 3:
        return fail("Arrange and Assert must be stated for each of the three test cases")

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
