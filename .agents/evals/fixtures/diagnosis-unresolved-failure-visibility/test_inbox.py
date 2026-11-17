import unittest
from inbox import Inbox


class Recovery(unittest.TestCase):
    def test_independent_success_keeps_recovery_for_unresolved_failure(self):
        inbox = Inbox()
        inbox.begin("a")
        inbox.fail("a")
        inbox.begin("b")
        inbox.accept("b")
        self.assertEqual(inbox.error, "Delivery failed")
        self.assertEqual(inbox.pending, {"a"})
        self.assertEqual(inbox.failed, {"a"})

    def test_external_acceptance_clears_the_last_unresolved_failure(self):
        inbox = Inbox()
        inbox.begin("a")
        inbox.fail("a")
        inbox.accept("a")
        self.assertIsNone(inbox.error)
        self.assertEqual(inbox.pending, set())

    def test_explicit_retry_clears_failure_but_preserves_pending_request(self):
        inbox = Inbox()
        inbox.begin("a")
        inbox.fail("a")
        inbox.retry()
        self.assertIsNone(inbox.error)
        self.assertEqual(inbox.pending, {"a"})
        inbox.accept("a")
        self.assertEqual(inbox.pending, set())


if __name__ == "__main__":
    unittest.main()
