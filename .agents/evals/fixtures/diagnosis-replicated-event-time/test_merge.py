import unittest
from merge import reconcile_event


class ReplicatedEventTest(unittest.TestCase):
    def test_replica_clock_difference_is_not_a_semantic_conflict(self):
        for kind, tick in [('open', 10), ('close', 12)]:
            early = {'id': 'sample', 'kind': kind, 'tick': 10, 'group': 'sample-group'}
            late = {**early, 'tick': 12}
            for left, right in [(early, late), (late, early)]:
                self.assertEqual(reconcile_event(left, right), {**early, 'tick': tick})
                self.assertEqual(early['tick'], 10)
                self.assertEqual(late['tick'], 12)

    def test_real_conflicts_and_unknown_kinds_stay_visible(self):
        start = {'id': 'sample', 'kind': 'open', 'tick': 10, 'group': 'sample-group'}
        for change in [{'group': 'different-group'}, {'id': 'different'}, {'kind': 'close'}]:
            self.assertIsNone(reconcile_event(start, {**start, **change, 'tick': 12}))
        result = {'id': 'result', 'kind': 'result', 'tick': 10, 'status': 'passed'}
        self.assertIsNone(reconcile_event(result, {**result, 'status': 'failed'}))
        self.assertIsNone(reconcile_event(result, {**result, 'tick': 12}))
        self.assertEqual(reconcile_event(result, dict(result)), result)


if __name__ == '__main__':
    unittest.main()
