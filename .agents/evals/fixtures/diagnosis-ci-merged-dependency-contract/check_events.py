import json
from pathlib import Path
import sys
import unittest

import schema_api

manifest = json.loads(Path("ci.json").read_text())
schema_api.API_VERSION = manifest["merged_dependency_api" if "--ci" in sys.argv else "local_dependency_api"]
if "--ci" in sys.argv:
    sys.argv.remove("--ci")

from events import parse_event


class EventContract(unittest.TestCase):
    def test_preserves_fields_when_stream_supplies_type(self):
        event = {"id": "event-a", "input": {"pages": [2, 5]}, "parent": "event-b"}
        self.assertEqual(parse_event(json.dumps(event), "agent.reply"), {**event, "type": "agent.reply"})

    def test_json_type_precedes_generic_stream_type(self):
        event = {"type": "agent.reply", "content": [{"text": "ok"}]}
        self.assertEqual(parse_event(json.dumps(event), "message"), event)

    def test_invalid_json_preserves_explicit_fallback(self):
        self.assertEqual(parse_event("unfinished", "agent.reply"), {"type": "agent.reply", "text": "unfinished"})

    def test_generic_invalid_objects_produce_no_event(self):
        self.assertIsNone(parse_event("[]", "message"))


if __name__ == "__main__":
    unittest.main()
