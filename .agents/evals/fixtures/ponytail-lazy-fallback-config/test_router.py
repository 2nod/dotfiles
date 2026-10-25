import unittest
from router import resolve_destination


class DestinationTests(unittest.TestCase):
    def test_explicit_destination_works_without_an_unused_default(self):
        settings = {}
        self.assertEqual(resolve_destination(settings, "custom-destination"), "custom-destination")
        self.assertEqual(settings, {})

    def test_explicit_destination_takes_precedence_and_preserves_settings(self):
        settings = {"DEFAULT_DESTINATION": "default-destination"}
        self.assertEqual(resolve_destination(settings, "custom-destination"), "custom-destination")
        self.assertEqual(settings, {"DEFAULT_DESTINATION": "default-destination"})

    def test_existing_default_only_callers_keep_their_destination(self):
        self.assertEqual(resolve_destination({"DEFAULT_DESTINATION": "default-destination"}), "default-destination")

    def test_missing_and_empty_defaults_still_fail_without_an_override(self):
        for settings in ({}, {"DEFAULT_DESTINATION": ""}):
            with self.subTest(settings=settings):
                with self.assertRaisesRegex(ValueError, "DEFAULT_DESTINATION is required"):
                    resolve_destination(settings)


if __name__ == "__main__":
    unittest.main()
