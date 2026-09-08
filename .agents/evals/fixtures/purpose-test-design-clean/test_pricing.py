import unittest
from pricing import total

class PricingTest(unittest.TestCase):
    def test_three_units_cost_six(self):
        self.assertEqual(total(2, 3), 6)
