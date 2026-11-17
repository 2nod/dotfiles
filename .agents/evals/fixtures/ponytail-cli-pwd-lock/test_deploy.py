import json
import os
from pathlib import Path
import tempfile

from deploy import deploy

with tempfile.TemporaryDirectory() as directory:
    parent = Path(directory)
    package = parent / "package"
    (package / "units/example").mkdir(parents=True)
    lock = package / "resource-lock.json"
    expected = {"./units/example": "resource_existing"}
    lock.write_text(json.dumps(expected))
    os.environ["PWD"] = str(parent)
    os.environ["SYNTHETIC_SETTING"] = "keep-me"
    deploy(package)
    deploy(package)
    assert json.loads(lock.read_text()) == expected, "A stale PWD creates a duplicate locked resource"
    assert os.environ["PWD"] == str(parent), "Do not mutate the parent's environment"
print("Package-relative identity and inherited environment preserved")
