import copy
import re
from bridge import Bridge
from upstream import Provider

for original_name in ["資料案内", "別の資料"]:
    for fail in [False, True]:
        provider = Provider(original_name, fail)
        bridge = Bridge(provider)
        saved = copy.deepcopy(provider.list_tools())
        tools = bridge.list_tools()
        assert [tool["name"] for tool in tools] == ["reference_qa"]
        assert re.fullmatch(r"[a-zA-Z0-9_-]{1,114}", tools[0]["name"])
        assert tools == [{**saved[0], "name": "reference_qa"}]
        args = {"query": "ping", "history": "synthetic history"}
        expected = {"content": [{"type": "text", "text": "ack"}], "structuredContent": {"answer": "ack"}, "isError": fail}
        assert bridge.call_tool("reference_qa", args) == expected
        assert args == {"query": "ping", "history": "synthetic history"}
        assert provider.calls == [(original_name, args)]
        for unknown in [original_name, "unknown_alias"]:
            try:
                bridge.call_tool(unknown, args)
            except ValueError:
                pass
            else:
                raise AssertionError("Unknown exposed names must be rejected")
        assert len(provider.calls) == 1
        assert provider.list_tools() == saved, "The unmanaged provider must not change"
print("Consumer naming, original dispatch and result preservation passed")
