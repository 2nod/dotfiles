#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import subprocess
import sys


SOURCE = '''def canonical_key(tenant_id: str, item_id: str) -> str:
    return f"{tenant_id}:{item_id}"


def legacy_key(item_id: str) -> str:
    return item_id
'''

TEST = '''import unittest

from src.cache_keys import canonical_key, legacy_key


class CacheKeyTest(unittest.TestCase):
    def test_canonical_key_is_tenant_scoped(self) -> None:
        self.assertEqual(canonical_key("tenant-a", "item-1"), "tenant-a:item-1")

    def test_legacy_key_remains_readable_during_rollout(self) -> None:
        self.assertEqual(legacy_key("item-1"), "item-1")


if __name__ == "__main__":
    unittest.main()
'''


def fail(message: str) -> int:
    print(message)
    return 1


def documents_contract(path: pathlib.Path) -> bool:
    text = path.read_text(encoding="utf-8").lower()
    return all(token in text for token in ("tenant_id", "item_id", "legacy", "fallback"))


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])

    if any((workspace / "docs" / "plans").glob("*.md")):
        return fail("completed implementation plan remains under docs/plans")

    design = workspace / "docs" / "design" / "cache-keys.md"
    notion = workspace / "local-notion" / "cache-keys.md"
    if not design.is_file() or not documents_contract(design):
        return fail("canonical design does not describe the implemented key contract")
    if not notion.is_file() or not documents_contract(notion):
        return fail("local Notion mirror is inconsistent with the implemented contract")

    if (workspace / "docs" / "adr").exists():
        return fail("an ADR was created even though no lasting decision required one")

    if (workspace / "src" / "cache_keys.py").read_text(encoding="utf-8") != SOURCE:
        return fail("implementation code changed during documentation closeout")
    if (workspace / "tests" / "test_cache_keys.py").read_text(encoding="utf-8") != TEST:
        return fail("tests changed during documentation closeout")

    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return fail("existing tests no longer pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
