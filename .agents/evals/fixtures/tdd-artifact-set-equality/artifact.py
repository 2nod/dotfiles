import hashlib
import json


def _fingerprint(values):
    payload = json.dumps(sorted(set(values)), separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def audit(generated, reference, expected_count):
    generated_set = set(generated)
    return {
        "success": len(generated_set) == expected_count,
        "missing": max(0, expected_count - len(generated_set)),
        "generated_set_sha256": _fingerprint(generated_set),
    }
