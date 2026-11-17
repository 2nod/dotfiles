import importlib
import unittest
import reader


class OwnerLifetime(unittest.TestCase):
    def setUp(self):
        importlib.reload(reader)

    def test_retained_owner_keeps_its_epoch_when_module_is_re_evaluated(self):
        owner = reader.create_owner('A')
        self.assertEqual([reader.advance(owner), reader.advance(owner)], [1, 2])
        importlib.reload(reader)
        self.assertEqual(reader.advance(owner), 3)
        self.assertEqual(owner['key'], 'A')

    def test_independent_owners_have_independent_epoch_sequences(self):
        first = reader.create_owner('A')
        second = reader.create_owner('B')
        self.assertEqual(reader.advance(first), 1)
        self.assertEqual(reader.advance(first), 2)
        self.assertEqual(reader.advance(second), 1)
        self.assertEqual(reader.advance(first), 3)


if __name__ == '__main__':
    unittest.main()
