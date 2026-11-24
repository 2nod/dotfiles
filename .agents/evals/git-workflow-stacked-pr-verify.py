from pathlib import Path
import subprocess
import sys


workspace = Path(sys.argv[1])
fixture = Path(sys.argv[2])


def git(*args):
    repo = (workspace / "repo").resolve()
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={repo}", "-C", str(repo), *args],
        text=True,
    ).strip()


def require(condition, message):
    if not condition:
        raise SystemExit(message)


require((workspace / "setup.py").read_bytes() == (fixture / "setup.py").read_bytes(),
        "The fixture setup changed.")
require(git("branch", "--format=%(refname:short)").splitlines()
        == ["activation", "main", "preparation"], "The branch set changed.")
require(git("rev-parse", "main") == git("rev-parse", "initial-main"), "main changed.")
for base, branch, path in (
    ("main", "preparation", "defaults.txt"),
    ("preparation", "activation", "feature.txt"),
):
    initial = f"initial-{branch}"
    require(git("merge-base", initial, branch) == git("rev-parse", initial),
            f"{branch} dropped existing commits.")
    require(git("merge-base", base, branch) == git("rev-parse", base),
            f"{branch} does not contain the current {base} tip.")
    require(git("diff", "--name-only", f"{base}...{branch}") == path,
            f"{branch} has an unexpected PR diff.")
    require(git("diff", initial, branch, "--", path) == "",
            f"{branch} changed the original feature content.")
