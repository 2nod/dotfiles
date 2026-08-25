import unittest

from model import initialize


class ModelTest(unittest.TestCase):
    def test_extended_shape(self):
        actor, critic = initialize(17, extended=True)
        self.assertEqual((len(actor), len(actor[0])), (2, 6))
        self.assertEqual(len(critic), 2)

if __name__ == "__main__":
    unittest.main()
