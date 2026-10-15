from copy import deepcopy
from audit import summarize

cases = [
    (
        {"status": "completed", "server_content": [{"type": "image"}],
         "preview_content": [{"type": "text", "text": "shortened notification"}],
         "expected_rows": ["38172954", "62048731"],
         "received_rows": ["38172954", "62048731"]},
        {"call_completed": True, "server_sent_image": True, "visual_receipt": "verified"},
    ),
    (
        {"status": "completed", "server_content": [{"type": "image"}],
         "preview_content": [{"type": "image"}],
         "expected_rows": ["38172954"], "received_rows": ["38172959"]},
        {"call_completed": True, "server_sent_image": True, "visual_receipt": "unverified"},
    ),
    (
        {"status": "completed",
         "server_content": [{"type": "text", "text": "Saved to /tmp/example.png"}],
         "preview_content": [{"type": "text", "text": "Saved to /tmp/example.png"}],
         "expected_rows": ["38172954"], "received_rows": [None]},
        {"call_completed": True, "server_sent_image": False, "visual_receipt": "no_image"},
    ),
    (
        {"status": "completed", "server_content": [{"type": "image"}],
         "preview_content": [{"type": "image"}],
         "expected_rows": [], "received_rows": []},
        {"call_completed": True, "server_sent_image": True, "visual_receipt": "unverified"},
    ),
]
for probe, expected in cases:
    original = deepcopy(probe)
    assert summarize(probe) == expected, (probe, summarize(probe), expected)
    assert probe == original, "Audit must not change observations"
print("PASS: sender, notification and receiver evidence remain separate")
