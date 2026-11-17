"""Run with an evaluated home.activation.updatePstack.data shell script as argv[1]."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def run(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def commit(repo):
    run("git", "-C", str(repo), "add", ".")
    run("git", "-C", str(repo), "-c", "user.name=Test", "-c",
        "user.email=test@example.invalid", "commit", "-qm", "fixture")


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for name in ("marketplace", "portable", "cursor")
            for p in (root / name).rglob("*") if p.is_file()}


with tempfile.TemporaryDirectory(prefix="pstack-update-test-") as temp:
    root = Path(temp)
    adapter, cursor, deployed = (root / name for name in ("adapter", "cursor", "deployed"))
    for repo in (adapter, cursor):
        run("git", "init", "-qb", "main", str(repo))
    plugin = adapter / "plugins/pstack"
    for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        write(plugin, manifest, json.dumps({"name": "pstack", "version": "1.0.0"}))
    write(adapter, ".claude-plugin/marketplace.json", json.dumps({
        "name": "pstack-claude", "plugins": [{"name": "pstack", "version": "1.0.0"}]}))
    write(plugin, "hooks/hooks.json", '{"hooks":{"SessionStart":[]}}')
    write(plugin, "hooks/codex-hooks.json", '{"hooks":{"SessionStart":[]}}')
    write(plugin, "skills/example/SKILL.md", "---\nname: example\n---\nfirst\n")
    write(plugin, "skills/obsolete/SKILL.md", "---\nname: obsolete\n---\n")
    write(plugin, "pi/index.ts", "// fixture\n")
    write(cursor, "pstack/skills/example/SKILL.md", "cursor first\n")
    commit(adapter)
    commit(cursor)
    script = Path(sys.argv[1]).read_text()
    script, count = re.subn(r'^[ \t]*pstackDir="[^"\n]+"$', f'pstackDir="{deployed}"', script, flags=re.M)
    assert count == 1, "Expected one activation destination"
    script = script.replace("https://github.com/michael-denyer/pstack-claude.git", adapter.as_uri())
    script = script.replace("https://github.com/cursor/plugins.git", cursor.as_uri())
    run("bash", "-c", script)
    first = snapshot(deployed)
    version = json.loads((deployed / "marketplace/plugins/pstack/.codex-plugin/plugin.json").read_text())["version"]
    assert version.startswith("1.0.0-dotfiles.")
    assert "name: pstack-example" in (deployed / "portable/skills/example/SKILL.md").read_text()
    for hook in ("hooks.json", "codex-hooks.json"):
        assert json.loads((deployed / f"marketplace/plugins/pstack/hooks/{hook}").read_text()) == {"hooks": {}}
    run("bash", "-c", script)
    assert snapshot(deployed) == first, "Rerunning must preserve the same contents"
    write(plugin, "skills/example/SKILL.md", "---\nname: example\n---\nlater\n")
    (plugin / "skills/obsolete/SKILL.md").unlink()
    write(cursor, "pstack/skills/example/SKILL.md", "cursor later\n")
    commit(adapter)
    commit(cursor)
    run("bash", "-c", script)
    updated = snapshot(deployed)
    assert updated != first
    assert "later" in (deployed / "portable/skills/example/SKILL.md").read_text()
    assert not (deployed / "portable/skills/obsolete/SKILL.md").exists()
    assert (deployed / "cursor/skills/example/SKILL.md").read_text() == "cursor later\n"
    assert json.loads((deployed / "marketplace/plugins/pstack/.codex-plugin/plugin.json").read_text())["version"] != version
    write(plugin, "skills/example/SKILL.md", "---\nname: example\n---\nthird\n")
    commit(adapter)
    failed = subprocess.run(["bash", "-c", script.replace(cursor.as_uri(), (root / "missing").as_uri())],
                            capture_output=True, text=True)
    assert failed.returncode != 0
    assert snapshot(deployed) == updated, "A failed fetch must keep the deployed version"
    print("PASS: first install, repeat, main advance, same-version cache refresh, deletion, fetch failure")
