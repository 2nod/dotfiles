"""Check retired deployments, including leftovers and unrelated local skills."""
import json
from pathlib import Path
import sys


def snapshot(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob('*') if p.is_file()
    }


def main():
    work, original = map(Path, sys.argv[1:3])
    try:
        config = json.loads((work / 'deployment.json').read_text())
        assert config == {'source': 'source', 'targets': ['runtime/shared']}, 'future deployment still targets legacy'
        for relative in ('source', 'runtime/shared', 'runtime/legacy/manual-helper'):
            assert snapshot(work / relative) == snapshot(original / relative), f'changed protected tree: {relative}'
        retired = work / 'runtime/legacy/review-helper'
        assert not retired.exists() and not retired.is_symlink(), 'managed skill remains in retired target'
        marker = work / 'runtime/legacy/.managed.json'
        if marker.exists():
            assert json.loads(marker.read_text()) == [], 'stale ownership marker'
    except (AssertionError, OSError, ValueError) as error:
        print(error)
        return 1
    print('PASS: future target removed; existing duplicate removed; source, shared bundle and manual skill preserved')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
