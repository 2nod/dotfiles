#!/usr/bin/env python3
"""Verify independent evidence categories, including CLI command expansion."""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


EXPECTED = {
    "cliSuccessCases": 3,
    "definitionLoadedCases": 2,
    "cases": [
        {"id": "case-a", "status": "confirmed", "evidence": "skill_tool"},
        {"id": "case-b", "status": "confirmed", "evidence": "command_expansion"},
        {"id": "case-c", "status": "unconfirmed", "evidence": "none"},
    ],
}

VOID_TAGS = set("area base br col embed hr img input link meta param source track wbr".split())


class CaseRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current = None
        self.frames = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        style = re.sub(r"\s+", "", (values.get("style") or "").lower())
        hidden = (tag in ("script", "style", "template", "noscript")
                  or "hidden" in values or values.get("aria-hidden") == "true"
                  or re.search(r"(?:^|;)(?:display:none|visibility:hidden)(?:!important)?(?:;|$)", style))
        if tag not in VOID_TAGS:
            self.frames.append((tag, hidden))
        if tag == "tr" and "data-case" in values:
            self.current = {
                "id": values["data-case"],
                "status": values.get("data-status"),
                "evidence": values.get("data-evidence"),
                "text": [],
            }

    def handle_endtag(self, tag):
        if tag == "tr" and self.current is not None:
            self.rows.append(self.current)
            self.current = None
        for index in range(len(self.frames) - 1, -1, -1):
            if self.frames[index][0] == tag:
                del self.frames[index:]
                break

    def handle_data(self, text):
        if self.current is not None and not any(hidden for _, hidden in self.frames):
            self.current["text"].append(text)


def verify(workspace, fixture):
    assert (workspace / "events.json").read_bytes() == (fixture / "events.json").read_bytes(), "Input changed"
    actual = json.loads((workspace / "report-data.json").read_text())
    assert actual == EXPECTED, "CLI success and skill evidence classification do not match the logs"
    page = CaseRows()
    page.feed((workspace / "index.html").read_text())
    assert len(page.rows) == len(EXPECTED["cases"]), "Missing or duplicate case rows"
    for row, expected in zip(page.rows, EXPECTED["cases"]):
        visible = set(re.findall(r"[\w-]+", " ".join(row.pop("text"))))
        assert row == expected, "HTML disagrees with the classified evidence"
        assert all(value in visible for value in expected.values()), "Case evidence is not visible"
    assert "](index.html)" in (workspace / "result.md").read_text(), "Missing report link"


if __name__ == "__main__":
    try:
        verify(Path(sys.argv[1]), Path(sys.argv[2]))
    except (AssertionError, OSError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
