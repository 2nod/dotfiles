import unittest
from pool import Pool


class Ownership(unittest.TestCase):
    def test_old_release_and_old_leave_preserve_new_registration(self):
        pool = Pool()
        first = pool.join('A', 1)
        second = pool.join('A', 2)
        self.assertFalse(first['open'])
        pool.release('A', first)
        pool.leave('A', 1)
        self.assertTrue(second['open'])

    def test_older_and_duplicate_join_are_rejected_without_closing_current(self):
        pool = Pool()
        current = pool.join('A', 2)
        self.assertIsNone(pool.join('A', 1))
        self.assertIsNone(pool.join('A', 2))
        self.assertTrue(current['open'])

    def test_leave_before_join_blocks_that_epoch_and_older_epochs(self):
        pool = Pool()
        pool.leave('A', 2)
        self.assertIsNone(pool.join('A', 1))
        self.assertIsNone(pool.join('A', 2))
        self.assertTrue(pool.join('A', 3)['open'])

    def test_releasing_current_closes_only_its_key_and_preserves_the_epoch(self):
        pool = Pool()
        first = pool.join('A', 1)
        other = pool.join('B', 1)
        pool.release('A', first)
        pool.release('A', first)
        self.assertFalse(first['open'])
        self.assertTrue(other['open'])
        self.assertIsNone(pool.join('A', 1))


if __name__ == '__main__':
    unittest.main()
