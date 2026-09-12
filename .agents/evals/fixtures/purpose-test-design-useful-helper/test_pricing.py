import unittest
from pricing import total
def make_order(price, quantity):
    return {'price': price, 'quantity': quantity, 'metadata': {'locale': 'ja'}}
class PricingTest(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(total(make_order(price=2, quantity=3)), 6)
    def test_zero(self):
        self.assertEqual(total(make_order(price=7, quantity=0)), 0)
