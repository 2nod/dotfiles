import json
from pathlib import Path
import shutil
import tempfile
from platform_runtime import submit


def check():
    source = Path(__file__).resolve().parent / "extension"
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        extension = root / "extension with spaces"
        shutil.copytree(source, extension)
        expected = [{"additional_context": "[dispatch] kind: arithmetic; revision: 3"}]
        assert submit(extension, root) == expected, "automatic BeforeMessage context is missing"
        assert "events" not in json.loads((source / "settings.json").read_text()), "settings is not an event registration location"
        declarations = json.loads((extension / "events/events.json").read_text())
        assert len(declarations["events"]["BeforeMessage"]) == 1, "event registered more than once"
    print("PASS: loader event and context from unrelated cwd and spaced path")


if __name__ == "__main__":
    check()
