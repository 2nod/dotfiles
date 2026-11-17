class Schema:
    def __init__(self, fields, strict=True):
        self.fields = tuple(fields)
        self.strict = strict

    def parse(self, value):
        if not isinstance(value, dict) or any(key not in value for key in self.fields):
            raise ValueError("Missing input")
        if self.strict and any(key not in self.fields for key in value):
            raise ValueError("Unknown input")
        return {key: value[key] for key in self.fields}


class Registry:
    def __init__(self):
        self.entries = {}

    def register(self, name, schema, callback):
        if not isinstance(schema, Schema):
            schema = Schema(schema, strict=False)
        self.entries[name] = schema, callback

    def call(self, name, value):
        schema, callback = self.entries[name]
        return callback(schema.parse(value))
