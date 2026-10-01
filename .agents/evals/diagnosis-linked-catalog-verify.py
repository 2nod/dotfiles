"""Run an independent copy of the public discovery check against the edited scanner."""
from pathlib import Path
import subprocess
import sys


def main():
    workspace, original = map(Path, sys.argv[1:3])
    try:
        result = subprocess.run(
            [sys.executable, '-B', '-c', (original / 'test_catalog.py').read_text()],
            cwd=workspace, capture_output=True, text=True, timeout=5,
        )
    except subprocess.TimeoutExpired:
        print('Directory discovery did not finish; check linked cycles')
        return 1
    print(result.stdout + result.stderr)
    return int(result.returncode != 0)


if __name__ == '__main__':
    raise SystemExit(main())
