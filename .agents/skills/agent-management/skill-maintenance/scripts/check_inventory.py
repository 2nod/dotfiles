"""Compare shared skill names and bundled contents; read-only, standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def files(root):
    if not root.is_dir():
        raise ValueError(f"missing directory: {root}")
    seen = set()
    for directory, dirs, names in os.walk(root, followlinks=True):
        real = Path(directory).resolve()
        if real in seen:
            raise ValueError(f"directory alias or cycle: {directory}")
        seen.add(real)
        dirs[:] = sorted(d for d in dirs if d not in {'.git', '__pycache__', '.ruff_cache'})
        for name in sorted(names):
            path = Path(directory) / name
            if not path.is_file():
                raise ValueError(f"not a regular file: {path}")
            yield path


def inventory(roots):
    result = {}
    for root in roots:
        for entry in files(root):
            if entry.name != 'SKILL.md':
                continue
            name = entry.parent.name
            if name in result:
                raise ValueError(f"duplicate skill name: {name}")
            digest = hashlib.sha256()
            for path in sorted(files(entry.parent)):
                digest.update(str(path.relative_to(entry.parent)).encode() + b'\0')
                digest.update(path.read_bytes() + b'\0')
            result[name] = digest.hexdigest()
    return result


def compare(expected, actual):
    return {
        'missing': sorted(expected.keys() - actual.keys()),
        'extra': sorted(actual.keys() - expected.keys()),
        'changed': sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', action='append', type=Path, required=True)
    parser.add_argument('--target', action='append', type=Path, required=True)
    args = parser.parse_args()
    try:
        expected = inventory(args.source)
        if not expected:
            raise ValueError('source inventory is empty')
        report = {str(p): compare(expected, inventory([p])) for p in args.target}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(any(any(diff.values()) for diff in report.values()))
    except (OSError, ValueError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
