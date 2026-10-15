import unittest
from adapter import to_error
from service import response_error


class ErrorContract(unittest.TestCase):
    def test_known_codes_keep_their_kind_locally_and_through_the_service(self):
        for code, kind, retryable in [
            ("STALE_VERSION", "conflict", False),
            ("IN_PROGRESS", "busy", True),
            ("NO_DOCUMENT", "not_found", False),
        ]:
            for error in [RuntimeError(code), response_error(code)]:
                with self.subTest(code=code, error_type=type(error).__name__):
                    self.assertEqual(to_error(error), {
                        "code": code, "kind": kind, "retryable": retryable,
                    })

    def test_unclassified_failures_do_not_retry(self):
        for error in [RuntimeError("record not found"), RuntimeError("UNKNOWN_FAILURE"),
                      response_error("UNRECOGNIZED"), None]:
            with self.subTest(error=error):
                self.assertFalse(to_error(error)["retryable"])
                self.assertNotEqual(to_error(error)["kind"], "unavailable")

    def test_connection_failures_can_retry(self):
        self.assertEqual(to_error(ConnectionError("link down")), {
            "code": "OPERATION_FAILED", "kind": "unavailable", "retryable": True,
        })


if __name__ == "__main__":
    unittest.main()
