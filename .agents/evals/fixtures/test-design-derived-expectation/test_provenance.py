import copy
import unittest

from provenance import validate


def branch_state():
    return {"farms": [{"money": 100}, {"money": 90}], "candidate_seat": 0}


def valid_record():
    return {
        "metric": "official_margin_delta",
        "student_branch": branch_state(),
        "teacher_branch": branch_state(),
        "student_margin": 10.0,
        "teacher_margin": 12.0,
        "delta": 2.0,
    }


class ProvenanceTests(unittest.TestCase):
    def test_valid_record(self):
        self.assertTrue(validate(valid_record()))

    def test_wrong_delta_is_rejected(self):
        record = copy.deepcopy(valid_record())
        record["delta"] = 3.0
        self.assertFalse(validate(record))


if __name__ == "__main__":
    unittest.main()
