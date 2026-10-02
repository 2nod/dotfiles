import unittest
from monitor import snapshot


class MonitorTest(unittest.TestCase):
    def test_saved_gaps_do_not_change_live_status(self):
        for gaps in (0, 1, 500):
            for kwargs, expected in [({}, 'ready'), ({'unread': 4}, 'loading'),
                                     ({'current_faults': 1}, 'error'), ({'paused': True}, 'stopped')]:
                with self.subTest(gaps=gaps, kwargs=kwargs):
                    self.assertEqual(snapshot(saved_gaps=gaps, **kwargs),
                                     {'state': expected, 'saved_gaps': gaps})


if __name__ == '__main__':
    unittest.main()
