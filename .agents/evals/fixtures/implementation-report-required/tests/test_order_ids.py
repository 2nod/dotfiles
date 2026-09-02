import unittest

from src.order_ids import normalize_order_id


class NormalizeOrderIdTest(unittest.TestCase):
    def test_trims_and_uppercases(self) -> None:
        self.assertEqual(normalize_order_id("  ab-12 "), "AB-12")

    def test_rejects_empty_result(self) -> None:
        with self.assertRaises(ValueError):
            normalize_order_id("   ")


if __name__ == "__main__":
    unittest.main()
