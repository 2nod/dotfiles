import unittest

from inventory import Inventory


class InventoryTest(unittest.TestCase):
    def test_reserve_reduces_available_stock(self) -> None:
        inventory = Inventory(10)
        self.assertEqual(inventory.reserve(3), 7)
        self.assertEqual(inventory.stock, 7)


if __name__ == "__main__":
    unittest.main()
