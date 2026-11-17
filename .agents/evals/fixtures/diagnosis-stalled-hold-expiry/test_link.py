import unittest
from link import Link


class Expiry(unittest.TestCase):
    def test_stalled_hold_expires_and_late_ack_reopens(self):
        link = Link()
        link.request("a")
        link.visible = False
        link.advance(9)
        self.assertTrue(link.connected)
        link.advance(1)
        self.assertFalse(link.connected)
        self.assertEqual(link.hold, "a")
        link.acknowledge()
        self.assertTrue(link.connected)
        link.advance(100)
        self.assertTrue(link.connected)

    def test_same_hold_does_not_extend_deadline_new_hold_gets_new_deadline(self):
        link = Link()
        link.visible = False
        link.request("a")
        link.advance(9)
        link.request("a")
        link.advance(1)
        self.assertFalse(link.connected)
        link.request("b")
        self.assertTrue(link.connected)
        link.advance(10)
        self.assertFalse(link.connected)

    def test_active_operation_outlives_deadline_and_failure_starts_new_wait(self):
        link = Link()
        link.visible = False
        link.request("a")
        link.advance(9)
        link.start_operation()
        link.advance(50)
        self.assertTrue(link.connected)
        link.finish_operation()
        link.advance(9)
        self.assertTrue(link.connected)
        link.advance(1)
        self.assertFalse(link.connected)
        link.acknowledge()
        self.assertTrue(link.connected)

    def test_visibility_and_other_links_are_independent(self):
        link, other = Link(), Link()
        link.request("a")
        other.request("b")
        other.visible = False
        link.advance(10)
        self.assertTrue(link.connected)
        link.visible = False
        self.assertFalse(link.connected)
        self.assertTrue(other.connected)
        link.visible = True
        self.assertTrue(link.connected)


if __name__ == "__main__":
    unittest.main()
