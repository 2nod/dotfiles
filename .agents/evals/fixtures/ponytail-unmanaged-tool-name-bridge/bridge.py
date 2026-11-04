class Bridge:
    def __init__(self, provider):
        self.provider = provider

    def list_tools(self):
        return self.provider.list_tools()

    def call_tool(self, name, arguments):
        return self.provider.call_tool(name, arguments)
