class Provider:
    def __init__(self, name, fail=False):
        self.tool = {"name": name, "description": "Reference QA", "inputSchema": {"query": "string"}}
        self.calls = []
        self.fail = fail

    def list_tools(self):
        return [self.tool]

    def call_tool(self, name, arguments):
        if name != self.tool["name"]:
            raise ValueError("Unknown upstream tool")
        self.calls.append((name, arguments.copy()))
        return {"content": [{"type": "text", "text": "ack"}], "structuredContent": {"answer": "ack"}, "isError": self.fail}
