import unittest
from ledger import Ledger


class LedgerTests(unittest.TestCase):
    def loaded(self):
        ledger = Ledger()
        request = ledger.begin()
        ledger.complete(request, [])
        return ledger

    def test_initial_and_reloading_reads_block_new_work(self):
        ledger = Ledger()
        self.assertFalse(ledger.can_start("fresh"))
        request = ledger.begin()
        self.assertFalse(ledger.can_start("fresh"))
        ledger.complete(request, [])
        self.assertTrue(ledger.can_start("fresh"))
        ledger.begin()
        self.assertFalse(ledger.can_start("fresh"))

    def test_refresh_preserves_known_completed_ids(self):
        ledger = self.loaded()
        ledger.record("done")
        request = ledger.begin()
        self.assertEqual(ledger.completed, {"done"})
        ledger.complete(request, [])
        self.assertFalse(ledger.can_start("done"))
        self.assertTrue(ledger.can_start("fresh"))

    def test_stale_read_cannot_erase_write_that_finished_after_request_started(self):
        ledger = self.loaded()
        request = ledger.begin()
        ledger.record("just-finished")
        ledger.complete(request, ["server-known"])
        self.assertEqual(ledger.completed, {"just-finished", "server-known"})
        self.assertFalse(ledger.can_start("just-finished"))

    def test_canceled_read_cannot_end_or_replace_newer_read(self):
        ledger = self.loaded()
        old = ledger.begin()
        ledger.cancel(old)
        current = ledger.begin()
        ledger.complete(old, ["canceled-value"])
        self.assertTrue(ledger.loading)
        self.assertEqual(ledger.completed, set())
        ledger.complete(current, ["current-value"])
        self.assertEqual(ledger.completed, {"current-value"})
        self.assertFalse(ledger.loading)

    def test_completed_reads_are_idempotent_and_ledgers_stay_independent(self):
        first, second = self.loaded(), self.loaded()
        request = first.begin()
        first.complete(request, ["one", "one"])
        first.complete(request, ["late-value"])
        self.assertEqual(first.completed, {"one"})
        self.assertEqual(second.completed, set())
        self.assertTrue(second.can_start("one"))


if __name__ == "__main__":
    unittest.main()
