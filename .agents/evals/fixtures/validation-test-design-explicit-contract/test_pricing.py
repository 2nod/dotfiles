import unittest
from pricing import total
def make_order(price, quantity):
    return {'price': price, 'quantity': quantity, 'metadata': {'locale': 'ja'}}
class TestPricing(unittest.TestCase):
    def test_three_units_at_two_cost_six(self):
        self.assertEqual(total(make_order(price=2, quantity=3)), 6)
    def test_zero_units_cost_zero(self):
        self.assertEqual(total(make_order(price=2, quantity=0)), 0)
