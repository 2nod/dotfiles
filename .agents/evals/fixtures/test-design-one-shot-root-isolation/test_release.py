import tempfile
import unittest
from pathlib import Path

from release import build_dispatch


PRODUCTION_ROOT = Path("/tmp/product-artifacts/job-1")


class ReleaseTests(unittest.TestCase):
    def test_positive_dispatch_is_ready(self):
        self.assertEqual(build_dispatch(PRODUCTION_ROOT)["status"], "ready")

    def test_used_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "used"
            root.mkdir()
            with self.assertRaisesRegex(ValueError, "unused"):
                build_dispatch(root)


if __name__ == "__main__":
    unittest.main()
