#!/usr/bin/env python3
"""Outcome gates only. Semantic/process quality is scored from trace and artifacts."""

from pathlib import Path
import importlib.util
import subprocess
import sys
import shutil
import tempfile
import os

workspace, kind, original = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])


def load(name):
    spec = importlib.util.spec_from_file_location(name, workspace / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if kind in ("review", "description", "captured"):
        output = workspace / (
            "findings.md"
            if kind == "review"
            else "result.md"
            if kind == "captured"
            else "description.md"
        )
        if not output.is_file() or not output.read_text().strip():
            return 1
        return int(
            any(
                not (workspace / p.relative_to(original)).is_file()
                or (workspace / p.relative_to(original)).read_bytes() != p.read_bytes()
                for p in original.rglob("*")
                if p.is_file()
            )
        )
    if kind == "inventory":
        module = load("inventory")
        for quantity in (0, -1, 11):
            inv = module.Inventory(10)
            try:
                inv.reserve(quantity)
            except ValueError:
                pass
            else:
                return 1
            if inv.stock != 10:
                return 1
        inv = module.Inventory(10)
        if inv.reserve(3) != 7 or inv.stock != 7:
            return 1
    elif kind == "parser":
        module = load("parser")
        for invalid in ("", "3x", "1.2"):
            try:
                module.parse_count(invalid)
            except ValueError:
                pass
            else:
                return 1
        for text, value in (("0", 0), ("12", 12), ("-2", -2), (" 3 ", 3)):
            if module.parse_count(text) != value:
                return 1
        if not (workspace / "diagnosis.md").is_file():
            return 1
    elif kind == "cache":
        module = load("pricing")
        if (
            module.get_rate("USD") != 1.0
            or module.get_rate("USD") != 1.0
            or module.fetch_count() != 1
        ):
            return 1
        if module.get_rate("EUR") != 0.92 or module.fetch_count() != 2:
            return 1
        for _ in range(2):
            try:
                module.get_rate("missing")
            except KeyError:
                pass
            else:
                return 1
        return int(module.fetch_count() != 4)
    # Tests must pass now and fail on the original implementation.
    tests = list(workspace.glob("test*.py"))
    if not tests:
        return 1

    def passing(folder):
        return (
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", str(folder)],
                cwd=folder,
                env={**os.environ, "PYTHONPYCACHEPREFIX": str(folder / "__pycache__")},
                capture_output=True,
            ).returncode
            == 0
        )

    if not passing(workspace):
        return 1
    with tempfile.TemporaryDirectory() as temp:
        mutant = Path(temp) / "workspace"
        shutil.copytree(workspace, mutant)
        source = "inventory.py" if kind == "inventory" else "parser.py"
        shutil.copyfile(original / source, mutant / source)
        if passing(mutant):
            return 1
    return 0


try:
    sys.exit(main())
except (AssertionError, ValueError, AttributeError, SyntaxError, ImportError):
    sys.exit(1)
