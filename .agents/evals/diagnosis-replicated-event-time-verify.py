"""Run the original public check against the edited synthetic merger."""
from pathlib import Path
import subprocess
import sys


def main():
    workspace, original = map(Path, sys.argv[1:3])
    try:
        result = subprocess.run(
            [sys.executable, '-B', '-c', (original / 'test_merge.py').read_text()],
            cwd=workspace, capture_output=True, text=True, timeout=5,
        )
    except subprocess.TimeoutExpired:
        print('Event reconciliation did not finish')
        return 1
    print(result.stdout + result.stderr)
    return int(result.returncode != 0)


if __name__ == '__main__':
    raise SystemExit(main())
