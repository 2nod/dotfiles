import copy
import json
from receipts import summarize

def call(tool, content, status="completed"):
    return {"tool": tool, "status": status, "result": {"content": content}}

native = call("screenshot", [{"type": "image", "data": "c3ludGhldGlj"}])
serialized = call("screenshot", [{"type": "text", "text": json.dumps(native["result"])}])
truncated = '{"rows": [ ...15 chars truncated... ]}'
nested = call("read", [{"type": "text", "text": json.dumps({"content": [{"type": "text", "text": truncated}]})}])
caption = call("read", [{"type": "text", "text": json.dumps({"caption": "chars truncated is a quoted label"})}])
metadata_only = call("screenshot", [{"type": "text", "text": "Screenshot stored; no image attached."}])
checks = [
    ([native], {"execution_complete": True, "visual_inputs": 1, "responses_complete": True}),
    ([serialized], {"execution_complete": True, "visual_inputs": 0, "responses_complete": True}),
    ([nested], {"execution_complete": True, "visual_inputs": 0, "responses_complete": False}),
    ([caption, metadata_only], {"execution_complete": True, "visual_inputs": 0, "responses_complete": True}),
    ([call("read", [], status="failed")], {"execution_complete": False, "visual_inputs": 0, "responses_complete": True}),
    ([native, serialized, nested], {"execution_complete": True, "visual_inputs": 1, "responses_complete": False}),
]
for packets, expected in checks:
    saved = copy.deepcopy(packets)
    actual = summarize(packets)
    assert actual == expected, (actual, expected)
    assert packets == saved, "Receipt inputs must remain unchanged"
print("Native image channels and nested response completeness passed")
