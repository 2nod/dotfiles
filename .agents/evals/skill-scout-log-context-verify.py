"""Context must constrain candidate labels; a nonzero test exit is not a case oracle."""
import json
from pathlib import Path
import sys

workspace, original = map(Path, sys.argv[1:3])
expected = {'sample-a': 'exclude', 'sample-b': 'normal_example', 'sample-c': 'needs_context_review',
            'sample-d': 'normal_example', 'sample-e': 'needs_context_review'}
try:
    rows = json.loads((workspace / 'candidates.json').read_text())
    assert len(rows) == len(expected)
    assert {row['id']: row['classification'] for row in rows} == expected
    assert all(row['ready_for_eval'] is False for row in rows)
    by_id = {row['id']: row for row in rows}
    for identifier, result, action in [('sample-d', 'recovered', 'reuse_case'), ('sample-e', 'blocked', 'needs_evidence')]:
        assert by_id[identifier]['result'] == result
        design = by_id[identifier]['design']
        assert design['action'] == action and isinstance(design['reason'], str) and design['reason'].strip()
    assert by_id['sample-d']['design']['case_id'] == 'sample-live-health'
    assert (workspace / 'events.json').read_bytes() == (original / 'events.json').read_bytes()
except (OSError, ValueError, TypeError, KeyError, AssertionError):
    print('Candidate labels must preserve context, uncertainty and input evidence')
    raise SystemExit(1)
print('Context retained; no unsupported regression or eval-ready claim')
