import unittest
from pricing import total
class PricingTest(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(total(7, 0), 0)
