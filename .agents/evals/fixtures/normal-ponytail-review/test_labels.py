import unittest
from labels import normalize_label


class LabelTests(unittest.TestCase):
    def test_contract(self):
        for value, expected in [("  Demo  ", "demo"), ("", ""), (" A B ", "a b"), ("  MIXED_Case ", "mixed_case"), ("Straße", "straße")]:
            with self.subTest(value=value):
                self.assertEqual(normalize_label(value), expected)
