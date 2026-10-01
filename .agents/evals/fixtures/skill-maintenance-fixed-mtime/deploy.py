"""Deploy local skill files, using metadata to skip unchanged files."""
from pathlib import Path
import shutil
import sys


def deploy(source, target):
    for path in source.rglob('*'):
        if not path.is_file():
            continue
        dest = target / path.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and (path.stat().st_size, path.stat().st_mtime_ns) == (dest.stat().st_size, dest.stat().st_mtime_ns):
            continue
        shutil.copy2(path, dest)


if __name__ == '__main__':
    deploy(Path(sys.argv[1]), Path(sys.argv[2]))
