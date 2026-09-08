import unittest
from pricing import total

def setup_order():
    return (2, 3)

class PricingTest(unittest.TestCase):
    def test_three_units_cost_six(self):
        self.assertEqual(total(*setup_order()), 6)
