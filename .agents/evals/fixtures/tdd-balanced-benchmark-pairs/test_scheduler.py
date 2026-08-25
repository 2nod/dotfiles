import unittest

from scheduler import build_schedule


class SchedulerTest(unittest.TestCase):
    def test_keeps_all_physical_runs(self):
        members = [(f"member-{index}", (index,)) for index in range(8)] + [("same-member-control", (0,))]
        self.assertEqual(len(build_schedule(members, (7, 0), 144)), 18)


if __name__ == "__main__":
    unittest.main()
