#!/usr/bin/env python3
"""Check schema classification and visible HTML rows, independent of quoting."""

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys


VOID_TAGS = set("area base br col embed hr img input link meta param source track wbr".split())


class CaseRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.frames = []
        self.rows = []
        self.current = None
        self.text = []

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
                "id": values["data-case"], "passed": values.get("data-passed"), "text": []
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
        if any(hidden for _, hidden in self.frames):
            return
        self.text.append(text)
        if self.current is not None:
            self.current["text"].append(text)


def verify(workspace, fixture):
    assert (workspace / "inputs.json").read_bytes() == (fixture / "inputs.json").read_bytes(), "inputs changed"
    source = json.loads((fixture / "inputs.json").read_text())
    expected = []
    for observation in source["observations"]:
        arguments = observation["arguments"]
        scope = arguments.get("scope", {})
        passed = (
            isinstance(arguments.get("taskId"), str) and bool(arguments["taskId"])
            and all(type(scope.get(key)) is int for key in source["registeredSchema"]["scopeRequired"])
            and all(key not in arguments or type(arguments[key]) is int
                    for key in source["registeredSchema"]["optionalInteger"])
        )
        expected.append({"id": observation["id"], "passed": passed})
    data = json.loads((workspace / "report-data.json").read_text())
    assert data["records"] == expected, "contract records incorrect"
    assert (data["calls"], data["passed"], data["failed"]) == (3, 1, 2), "contract counts incorrect"
    page = CaseRows()
    page.feed((workspace / "index.html").read_text())
    assert len(page.rows) == len(expected), "missing or duplicate case rows"
    assert {row["id"] for row in page.rows} == {record["id"] for record in expected}, "HTML cases differ"
    for record in expected:
        row = next(row for row in page.rows if row["id"] == record["id"])
        passed = str(record["passed"]).lower()
        assert row["passed"] == passed, "HTML classification differs"
        visible = set(re.findall(r"[\w-]+", " ".join(row["text"]).lower()))
        assert record["id"] in visible and passed in visible, "visible result missing"
    visible = " ".join(page.text)
    assert "入力契約" in visible and ("mock" in visible.lower() or "合成" in visible), "scope missing"
    assert "](index.html)" in (workspace / "result.md").read_text(), "artifact link missing"


if __name__ == "__main__":
    try:
        verify(Path(sys.argv[1]), Path(sys.argv[2]))
    except (AssertionError, KeyError, OSError, ValueError) as error:
        print("FAIL:", error, file=sys.stderr)
        raise SystemExit(1)
    print("PASS: input schema evidence")
