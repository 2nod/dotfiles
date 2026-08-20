#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import sys


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    spec = importlib.util.spec_from_file_location("pricing", workspace / "pricing.py")
    if not spec or not spec.loader:
        print("pricing.py could not be loaded")
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if module.get_rate("USD") != 1.0 or module.get_rate("USD") != 1.0:
        return fail("same currency returned an unexpected rate")
    if module.fetch_count() != 1:
        return fail(f"same currency fetched {module.fetch_count()} times; expected 1")
    if module.get_rate("EUR") != 0.92 or module.fetch_count() != 2:
        return fail(
            f"different currency fetch count was {module.fetch_count()}; expected 2"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
