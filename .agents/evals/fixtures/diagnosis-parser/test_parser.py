import unittest

from parser import parse_count  # type: ignore[attr-defined]


class ParserTest(unittest.TestCase):
    def test_valid_count_is_parsed(self) -> None:
        self.assertEqual(parse_count(" 12 "), 12)


if __name__ == "__main__":
    unittest.main()
