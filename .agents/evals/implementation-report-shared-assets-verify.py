#!/usr/bin/env python3
"""Check supplied CSS preservation and local inclusion, not reading quality."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re
import sys


class Styles(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.inert_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("template", "noscript"):
            self.inert_depth += 1
        values = {}
        for name, value in attrs:
            values.setdefault(name, value)
        rel = (values.get("rel") or "").lower().split()
        if (tag == "link" and not self.inert_depth
                and "stylesheet" in rel and "alternate" not in rel
                and "disabled" not in values
                and (values.get("media") or "all").strip().lower() in ("", "all", "screen")):
            self.hrefs.append(values.get("href", ""))

    def handle_endtag(self, tag):
        if tag in ("template", "noscript"):
            self.inert_depth = max(0, self.inert_depth - 1)


def verify(workspace, fixture):
    for original in fixture.rglob("*"):
        if original.is_file():
            candidate = workspace / original.relative_to(fixture)
            if not candidate.is_file() or candidate.read_bytes() != original.read_bytes():
                return "input changed: " + str(original.relative_to(fixture))
    report_dir = workspace / "report"
    report = report_dir / "index.html"
    if not report.is_file():
        return "report/index.html missing"
    result = workspace / "result.md"
    if not result.is_file() or not re.search(r"\[[^\]]+\]\(report/index\.html\)", result.read_text()):
        return "result.md must link report/index.html"
    parser = Styles()
    parser.feed(report.read_text())
    css = (fixture / "shared-assets/document.css").read_bytes()
    for href in parser.hrefs:
        url = urlsplit(href)
        if url.scheme or url.netloc or not url.path or Path(unquote(url.path)).is_absolute():
            continue
        asset = (report_dir / unquote(url.path)).resolve()
        if asset.is_relative_to(report_dir.resolve()) and asset.is_file() and asset.read_bytes() == css:
            return None
    return "supplied shared CSS must be bundled inside report and linked as an active local stylesheet"


if __name__ == "__main__":
    error = verify(Path(sys.argv[1]), Path(sys.argv[2]))
    if error:
        print(error, file=sys.stderr)
    raise SystemExit(1 if error else 0)
