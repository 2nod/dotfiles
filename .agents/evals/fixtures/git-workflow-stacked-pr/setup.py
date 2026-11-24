import os
from pathlib import Path
import subprocess


repo = Path("repo")
repo.mkdir()
env = {
    **os.environ,
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
}


def git(*args):
    subprocess.run(["git", "-C", str(repo), *args], env=env, check=True)


def commit_file(name, content, message):
    (repo / name).write_text(content, encoding="utf-8")
    git("add", name)
    git("commit", "-qm", message)


git("init", "-q", "-b", "main")
git("config", "user.name", "Synthetic")
git("config", "user.email", "synthetic@example.invalid")
git("config", "commit.gpgsign", "false")
git("config", "core.hooksPath", "/dev/null")
commit_file("readme.txt", "Initial configuration\n", "Initial commit")
git("switch", "-qc", "preparation")
commit_file("defaults.txt", "mode=standard\n", "Prepare defaults")
git("tag", "initial-preparation")
git("switch", "-qc", "activation")
commit_file("feature.txt", "enabled=true\n", "Enable feature")
git("switch", "-q", "main")
commit_file("maintenance.txt", "schedule=weekly\n", "Set maintenance schedule")
git("tag", "initial-main")
git("switch", "-q", "activation")
git("merge", "--no-edit", "main")
git("tag", "initial-activation")
