#!/usr/bin/env python3
"""Structural report gate. Meaning and readability require artifact review."""

import sys
from pathlib import Path
from html.parser import HTMLParser


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.body = False
        self.heading = False
        self.text = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.body = True
        if tag in ("h1", "h2"):
            self.heading = True
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if self.body and not self.hidden:
            self.text.append(data)


def verify(workspace, original):
    for source in original.rglob("*"):
        if source.is_file():
            output = workspace / source.relative_to(original)
            if not output.is_file() or output.read_bytes() != source.read_bytes():
                return 1
    target = workspace / "index.html"
    pointer = workspace / "result.md"
    if not target.is_file() or not pointer.is_file():
        return 1
    if "](index.html)" not in pointer.read_text():
        return 1
    page = Page()
    page.feed(target.read_text())
    return int(not (page.body and page.heading and "".join(page.text).strip()))


if __name__ == "__main__":
    raise SystemExit(verify(Path(sys.argv[1]), Path(sys.argv[2])))
