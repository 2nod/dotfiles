import unittest

from reconcile import reconcile


class ManifestLedgerParityTest(unittest.TestCase):
    def test_lifecycle_display_mismatch_is_stale(self):
        result = reconcile(
            {"lifecycle": "active", "display_status": "進行中"},
            {"lifecycle": "pr_open", "display_status": "PR準備中"},
        )
        self.assertEqual(result["status"], "stale")

    def test_valid_merged_receipt_projects_reconciled(self):
        result = reconcile(
            {"lifecycle": "pr_open", "display_status": "PR準備中"},
            {"lifecycle": "pr_open", "display_status": "PR準備中"},
            {"valid": True},
        )
        self.assertEqual(result, {"status": "reconciled", "lifecycle": "reconciled"})

    def test_missing_receipt_is_stale(self):
        result = reconcile(
            {"lifecycle": "pr_open", "display_status": "PR準備中"},
            {"lifecycle": "pr_open", "display_status": "PR準備中"},
        )
        self.assertEqual(result["status"], "stale")


if __name__ == "__main__":
    unittest.main()
