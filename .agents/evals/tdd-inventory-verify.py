#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

BUGGY = """class Inventory:
    def __init__(self, stock: int) -> None:
        self.stock = stock

    def reserve(self, quantity: int) -> int:
        self.stock -= quantity
        if quantity <= 0 or self.stock < 0:
            raise ValueError("invalid quantity")
        return self.stock
"""


def tests_pass(workspace: pathlib.Path) -> bool:
    with tempfile.TemporaryDirectory() as cache:
        return (
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", str(workspace)],
                env={**os.environ, "PYTHONPYCACHEPREFIX": cache},
                capture_output=True,
                text=True,
                check=False,
            ).returncode
            == 0
        )


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    spec = importlib.util.spec_from_file_location(
        "inventory", workspace / "inventory.py"
    )
    if not spec or not spec.loader:
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    inventory = module.Inventory(10)
    try:
        inventory.reserve(0)
    except ValueError:
        rejected = True
    else:
        rejected = False
    if not rejected:
        return fail("reserve(0) was accepted; expected ValueError")
    if inventory.stock != 10:
        return fail(f"stock changed to {inventory.stock} after rejection; expected 10")
    if not tests_pass(workspace):
        return fail("regression test suite failed")

    with tempfile.TemporaryDirectory() as temp:
        mutant = pathlib.Path(temp) / "workspace"
        shutil.copytree(workspace, mutant)
        (mutant / "inventory.py").write_text(BUGGY, encoding="utf-8")
        if tests_pass(mutant):
            return fail("regression tests do not detect the original mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
