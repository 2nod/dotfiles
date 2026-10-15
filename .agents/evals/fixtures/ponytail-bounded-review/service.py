import json
MAX_BYTES = 4096
def encode(report):
    data = json.dumps(report, separators=(",", ":")).encode()
    if len(data) > MAX_BYTES:
        raise ValueError("summary exceeds fixed request cap")
    return data
