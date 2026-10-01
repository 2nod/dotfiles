"""Exercise file contents independently of fixed size and modification time."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    script = Path(sys.argv[1]).resolve() / 'deploy.py'
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / 'source'
        target = Path(directory) / 'target'
        initial = {
            'review-helper/SKILL.md': b'---\nname: review-helper\n---\nRead references/checklist.md.\n',
            'review-helper/references/checklist.md': b'revision=aaaa\n',
        }
        for relative, content in initial.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            os.utime(path, ns=(1000000000, 1000000000))

        def run():
            result = subprocess.run([sys.executable, str(script), str(source), str(target)], capture_output=True, timeout=10)
            assert result.returncode == 0, 'deployment failed'
            for relative in initial:
                assert (source / relative).read_bytes() == (target / relative).read_bytes(), f'stale content: {relative}'

        run()
        for relative in initial:
            path = source / relative
            content = path.read_bytes().replace(b'aaaa', b'bbbb').replace(b'Read', b'Use:')
            path.write_bytes(content)
            os.utime(path, ns=(1000000000, 1000000000))
        run()
    print('PASS: equal-size, fixed-timestamp changes refresh skill and reference contents')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.TimeoutExpired) as error:
        print(error)
        raise SystemExit(1)
