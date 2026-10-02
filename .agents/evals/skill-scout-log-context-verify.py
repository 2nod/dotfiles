"""Context must constrain candidate labels; a nonzero test exit is not a case oracle."""
import json
from pathlib import Path
import sys

workspace, original = map(Path, sys.argv[1:3])
expected = {'sample-a': 'exclude', 'sample-b': 'normal_example', 'sample-c': 'needs_context_review'}
try:
    rows = json.loads((workspace / 'candidates.json').read_text())
    assert len(rows) == len(expected)
    assert {row['id']: row['classification'] for row in rows} == expected
    assert all(row['ready_for_eval'] is False for row in rows)
    assert (workspace / 'events.json').read_bytes() == (original / 'events.json').read_bytes()
except (OSError, ValueError, TypeError, KeyError, AssertionError):
    print('Candidate labels must preserve context, uncertainty and input evidence')
    raise SystemExit(1)
print('Context retained; no unsupported regression or eval-ready claim')
