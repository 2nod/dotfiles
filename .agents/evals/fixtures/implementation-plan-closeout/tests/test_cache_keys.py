import unittest

from src.cache_keys import canonical_key, legacy_key


class CacheKeyTest(unittest.TestCase):
    def test_canonical_key_is_tenant_scoped(self) -> None:
        self.assertEqual(canonical_key("tenant-a", "item-1"), "tenant-a:item-1")

    def test_legacy_key_remains_readable_during_rollout(self) -> None:
        self.assertEqual(legacy_key("item-1"), "item-1")


if __name__ == "__main__":
    unittest.main()
