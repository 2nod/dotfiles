#!/usr/bin/env python3
"""Offline verifier for synthetic figure order, folio and immutable public notes."""
import json
from pathlib import Path
import re
import sys
from html.parser import HTMLParser


VOID_TAGS = set("area base br col embed hr img input link meta param source track wbr".split())


class Figures(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.rows = {}
        self.hidden = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        style = re.sub(r'\s+', '', (attrs.get('style') or '').lower())
        hidden = (tag in ('script', 'style', 'template', 'noscript')
                  or 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
                  or re.search(r'(?:^|;)(?:display:none|visibility:hidden)(?:!important)?(?:;|$)', style))
        if tag not in VOID_TAGS:
            self.hidden.append((tag, hidden))
        if tag == 'figure':
            self.current = attrs.get('data-case-id')
            assert self.current and self.current not in self.rows, 'missing or duplicate case'
            self.rows[self.current] = {'text': '', 'images': []}
        if tag == 'img' and self.current:
            self.rows[self.current]['images'].append(attrs.get('src'))

    def handle_endtag(self, tag):
        if tag == 'figure':
            self.current = None
        for index in range(len(self.hidden) - 1, -1, -1):
            if self.hidden[index][0] == tag:
                del self.hidden[index:]
                break

    def handle_data(self, text):
        if self.current and not any(hidden for _, hidden in self.hidden):
            self.rows[self.current]['text'] += text


def verify(workspace):
    fixture = Path(__file__).parent / 'fixtures/experiment-report-page-identity'
    source = json.loads((fixture / 'experiment-source.json').read_text())
    for name in ('experiment-source.json', *(p['source_file'] for p in source['pages'])):
        assert (workspace / name).read_bytes() == (fixture / name).read_bytes(), 'evidence changed'
    rows = json.loads((workspace / 'report-data.json').read_text())['cases']
    assert len(rows) == len(source['pages']), 'case omitted or duplicated'
    assert {r['case_id'] for r in rows} == {p['case_id'] for p in source['pages']}, 'case IDs changed'
    parser = Figures()
    parser.feed((workspace / 'report.html').read_text())
    assert set(parser.rows) == {p['case_id'] for p in source['pages']}, 'HTML case set differs'
    for expected in source['pages']:
        row = next(r for r in rows if r['case_id'] == expected['case_id'])
        assert all(row.get(k) == v for k, v in expected.items()), 'identity or public note changed'
        figure = parser.rows[expected['case_id']]
        assert figure['images'] == [expected['source_file']], 'image points to another case'
        text = figure['text']
        assert f"Manuscript {expected['manuscript_number']}" in text, 'manuscript order not qualified'
        assert f"Folio {expected['printed_folio']}" in text, 'printed folio not qualified'
        assert Path(expected['source_file']).name in text, 'source filename missing'
        assert expected['public_note'] in text, 'public note rewritten or associated with another case'


if __name__ == '__main__':
    try:
        verify(Path(sys.argv[1]))
    except (AssertionError, KeyError, ValueError, OSError) as error:
        print('FAIL:', error)
        sys.exit(1)
    print('PASS: figure identity, public note and visible source references agree')
