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
    upstream, deployed = (root / name for name in ("upstream", "deployed"))
    run("git", "init", "-qb", "main", str(upstream))
    plugin = upstream / "pstack"
    manifest = {"name": "pstack", "version": "1.0.0", "author": {"name": "Test"}}
    write(plugin, "plugin.json", json.dumps(manifest))
    write(plugin, ".cursor-plugin/plugin.json", json.dumps(manifest))
    write(plugin, "skills/example/SKILL.md", "---\nname: example\n---\nfirst\n")
    write(plugin, "skills/obsolete/SKILL.md", "---\nname: obsolete\n---\n")
    write(plugin, "assets/logo.svg", "<svg/>\n")
    write(deployed, "portable/pi/index.ts", "// stale extension\n")
    write(deployed, "marketplace/plugins/pstack/hooks/hooks.json", '{"hooks":{}}')
    commit(upstream)
    script = Path(sys.argv[1]).read_text()
    script, count = re.subn(r'^[ \t]*pstackDir="[^"\n]+"$', f'pstackDir="{deployed}"', script, flags=re.M)
    assert count == 1, "Expected one activation destination"
    assert script.count("https://github.com/") == 1, "Fetch only the official repository"
    script = script.replace("https://github.com/cursor/plugins.git", upstream.as_uri())
    run("bash", "-c", script)
    first = snapshot(deployed)
    version = json.loads((deployed / "marketplace/plugins/pstack/.codex-plugin/plugin.json").read_text())["version"]
    assert version.startswith("1.0.0-dotfiles.")
    for manifest_path in ("plugin.json", ".claude-plugin/plugin.json", ".cursor-plugin/plugin.json"):
        assert json.loads((deployed / "marketplace/plugins/pstack" / manifest_path).read_text())["version"] == version
    assert "name: pstack-example" in (deployed / "portable/skills/example/SKILL.md").read_text()
    assert not (deployed / "marketplace/plugins/pstack/hooks").exists()
    assert not (deployed / "portable/pi").exists()
    assert (deployed / "marketplace/plugins/pstack/skills/example/SKILL.md").read_bytes() == (plugin / "skills/example/SKILL.md").read_bytes()
    assert (deployed / "portable/assets/logo.svg").read_bytes() == (plugin / "assets/logo.svg").read_bytes()
    run("bash", "-c", script)
    assert snapshot(deployed) == first, "Rerunning must preserve the same contents"
    write(plugin, "skills/example/SKILL.md", "---\nname: example\n---\nlater\n")
    (plugin / "skills/obsolete/SKILL.md").unlink()
    commit(upstream)
    run("bash", "-c", script)
    updated = snapshot(deployed)
    assert updated != first
    assert "later" in (deployed / "portable/skills/example/SKILL.md").read_text()
    assert not (deployed / "portable/skills/obsolete/SKILL.md").exists()
    assert (deployed / "cursor/skills/example/SKILL.md").read_bytes() == (plugin / "skills/example/SKILL.md").read_bytes()
    assert json.loads((deployed / "marketplace/plugins/pstack/.codex-plugin/plugin.json").read_text())["version"] != version
    write(plugin, "skills/example/SKILL.md", "---\nname: example\n---\nthird\n")
    commit(upstream)
    failed = subprocess.run(["bash", "-c", script.replace(upstream.as_uri(), (root / "missing").as_uri())],
                            capture_output=True, text=True)
    assert failed.returncode != 0
    assert snapshot(deployed) == updated, "A failed fetch must keep the deployed version"
    print("PASS: first install, repeat, main advance, same-version cache refresh, deletion, fetch failure")
