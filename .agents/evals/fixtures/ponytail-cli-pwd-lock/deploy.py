import os
from pathlib import Path
import subprocess
import sys


def deploy(package):
    package = Path(package).resolve()
    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("resource_cli.py"))],
        cwd=package,
        env=os.environ.copy(),
        check=True,
    )
