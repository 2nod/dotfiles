#!/usr/bin/env python3
"""Deterministic, offline evidence/status verifier for a synthetic report."""
import hashlib
import json
import pathlib
import re
import sys
from html.parser import HTMLParser


VOID_TAGS = set("area base br col embed hr img input link meta param source track wbr".split())


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.frames = []
        self.visible = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        key = attrs.get('data-run-id') or ('reference' if attrs.get('id') == 'reference-status' else None)
        style = re.sub(r'\s+', '', (attrs.get('style') or '').lower())
        hidden = (tag in ('script', 'style', 'template', 'noscript')
                  or 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
                  or re.search(r'(?:^|;)(?:display:none|visibility:hidden)(?:!important)?(?:;|$)', style))
        if tag not in VOID_TAGS:
            self.frames.append((tag, key, hidden))
        if key:
            assert key not in self.visible, 'duplicate HTML run or reference'
            self.visible[key] = ''

    def handle_endtag(self, tag):
        for i in range(len(self.frames) - 1, -1, -1):
            if self.frames[i][0] == tag:
                del self.frames[i:]
                break

    def handle_data(self, text):
        if any(hidden for _, _, hidden in self.frames):
            return
        for _, key, _ in self.frames:
            if key:
                self.visible[key] += ' ' + text


def verify(workspace):
    fixture = pathlib.Path(__file__).parent / 'fixtures/experiment-report-completion-levels'
    source_path = workspace / 'experiment-source.json'
    assert hashlib.sha256(source_path.read_bytes()).digest() == hashlib.sha256((fixture / 'experiment-source.json').read_bytes()).digest(), 'source evidence changed'
    source = json.loads(source_path.read_text())
    report = json.loads((workspace / 'report-data.json').read_text())
    rows = report['runs']
    assert len(rows) == len(source['runs']), 'run omitted or duplicated'
    assert [r['id'] for r in rows] == [r['id'] for r in source['runs']], 'run IDs/order changed'
    parser = ReportParser()
    parser.feed((workspace / 'report.html').read_text())
    for recorded, row in zip(source['runs'], rows):
        failed = any(t.get('result', {}).get('ok') is False for t in recorded['tools'])
        submitted = any(t['name'] == 'submit' and t['result'].get('ok') is True for t in recorded['tools'])
        expected = 'failed' if failed else ('submitted' if submitted else 'not_saved')
        assert row['harness_success'] == recorded['harness_success'], 'harness evidence changed'
        assert row['workflow_status'] == expected, recorded['id'] + ': completion levels conflated'
        assert expected in parser.visible.get(row['id'], '').split(), row['id'] + ': HTML status differs'
    assert report['reference_status'] == source['reference_status'], 'unapproved reference promoted'
    assert source['reference_status'] in parser.visible.get('reference', '').split(), 'HTML reference approval differs'


if __name__ == '__main__':
    try:
        verify(pathlib.Path(sys.argv[1]))
    except (AssertionError, KeyError, ValueError, OSError) as error:
        print('FAIL:', error)
        sys.exit(1)
    print('PASS: source evidence, workflow levels, reference status and HTML agree')
