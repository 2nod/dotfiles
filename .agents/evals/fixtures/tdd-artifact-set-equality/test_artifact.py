import unittest

from artifact import audit


class ArtifactAuditTest(unittest.TestCase):
    def test_exact_set_is_accepted(self):
        result = audit(["b", "a"], ["a", "b"], 2)
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
