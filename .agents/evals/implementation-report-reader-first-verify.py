#!/usr/bin/env python3
from __future__ import annotations

import html
import pathlib
import re
import sys
from html.parser import HTMLParser


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1]).resolve()
    report = workspace.parent / "implementation-report" / "index.html"
    if not report.is_file():
        return fail("implementation report is missing outside the fixture workspace")
    if (workspace / "index.html").exists():
        return fail("implementation report was created inside the fixture workspace")

    raw = report.read_text(encoding="utf-8")
    parser = TextParser()
    parser.feed(raw)
    visible = re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()

    ordered_summary = (
        "翻訳済みコンテンツを再処理する運用機能",
        "翻訳結果を修正する運用担当者",
        "一つの項目だけ翻訳を直したいとき",
        "項目IDを受け取り、指定した項目の翻訳だけを更新する",
        "対象項目だけを安全に再実行できるようにする",
        "全項目を再実行する",
        "指定した項目だけを再実行する",
        "通常の全件実行経路は変えない",
    )
    try:
        positions = [visible.index(token) for token in ordered_summary]
    except ValueError as error:
        return fail(f"reader-facing change summary is incomplete: {error}")
    if positions != sorted(positions):
        return fail("context, purpose, Before, After, and unchanged boundary are not reader-first")

    first_summary_end = positions[-1]
    early_symbol = re.search(
        r"(?<![A-Za-z0-9])(?:A/B/C|H/P/U|A|B|C|H1|P1|U1)(?![A-Za-z0-9])",
        visible,
    )
    if early_symbol and early_symbol.start() < first_summary_end:
        return fail("an internal classification symbol appears before the change summary")

    for label, claim in (("Human", "H1"), ("Proven", "P1"), ("Unconfirmed", "U1")):
        if claim in visible and (label not in visible or visible.index(label) > visible.index(claim)):
            return fail(f"{label} must be defined before {claim} when the tag is used")

    required = (
        "対象IDは、再実行する項目を指定する識別子",
        "他の翻訳結果を作り直さずに修正を反映できる",
        "製品挙動",
        "対象IDで再実行範囲を絞る",
        "証拠",
        "局所再実行の回帰テストを追加",
        "1111111",
        "base/rerun.py",
        "working tree",
        "src/rerun.py",
    )
    missing = [token for token in required if token not in visible]
    if missing:
        return fail(f"runtime, evidence, or provenance details are missing: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
