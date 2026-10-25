"""Synthetic platform: event declarations load only from events/events.json."""
import json
import os
from pathlib import Path
import subprocess


def submit(extension, cwd):
    extension = Path(extension).resolve()
    config = extension / "events/events.json"
    if not config.exists():
        return []
    declarations = json.loads(config.read_text())["events"]
    return [json.loads(subprocess.check_output(
        command, shell=True, cwd=cwd, text=True,
        env={**os.environ, "EXTENSION_ROOT": str(extension)},
    )) for command in declarations.get("BeforeMessage", [])]
