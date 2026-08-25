#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


BUGGY = '''import hashlib
import json
import random


def _draw(rng, rows, columns):
    return [[rng.gauss(0.0, 0.01) for _ in range(columns)] for _ in range(rows)]


def initialize(seed, extended=False):
    rng = random.Random(seed)
    actor = _draw(rng, 2, 6 if extended else 4)
    critic = [rng.gauss(0.0, 0.01) for _ in range(2)]
    return actor, critic


def fingerprint(model):
    actor, critic = model
    return hashlib.sha256(json.dumps([actor, critic]).encode()).hexdigest()
'''


def load_module(workspace: pathlib.Path):
    spec = importlib.util.spec_from_file_location("model", workspace / "model.py")
    if not spec or not spec.loader:
        raise RuntimeError("could not load model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tests_pass(workspace: pathlib.Path) -> bool:
    with tempfile.TemporaryDirectory() as cache:
        return subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(workspace)],
            env={**os.environ, "PYTHONPYCACHEPREFIX": cache},
            capture_output=True,
            text=True,
            check=False,
        ).returncode == 0


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    module = load_module(workspace)
    base_actor, base_critic = module.initialize(17)
    extended_actor, extended_critic = module.initialize(17, extended=True)
    repeated_actor, _ = module.initialize(17, extended=True)
    if [row[:4] for row in extended_actor] != base_actor:
        return fail("existing actor columns changed")
    if extended_critic != base_critic:
        return fail("critic changed")
    if [row[4:] for row in extended_actor] != [row[4:] for row in repeated_actor]:
        return fail("extension columns are nondeterministic")
    if module.fingerprint((base_actor, base_critic)) == module.fingerprint(
        (extended_actor, extended_critic)
    ):
        return fail("model fingerprint does not identify extension")
    if not tests_pass(workspace):
        return fail("regression test suite failed")
    with tempfile.TemporaryDirectory() as temp:
        mutant = pathlib.Path(temp) / "workspace"
        shutil.copytree(workspace, mutant)
        (mutant / "model.py").write_text(BUGGY, encoding="utf-8")
        if tests_pass(mutant):
            return fail("tests do not detect naive row-major shape expansion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
