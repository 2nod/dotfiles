import unittest

from event_alignment import labels_for_observations


class EventAlignmentTest(unittest.TestCase):
    def test_returns_one_row_per_observation(self):
        steps = [
            {"observation": "o0", "action": None},
            {"observation": "o1", "action": "a0"},
        ]

        self.assertEqual(len(labels_for_observations(steps)), 2)


if __name__ == "__main__":
    unittest.main()
