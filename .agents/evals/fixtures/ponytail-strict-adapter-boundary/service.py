from framework import Registry, Schema

registry = Registry()
calls = {"label": 0, "quantity": 0, "open": 0}


def declare(name, schema):
    def handle(value):
        parsed = schema.parse(value)
        calls[name] += 1
        return parsed
    registry.register(name, schema.fields, handle)


declare("label", Schema(["title"]))
declare("quantity", Schema(["units"]))
declare("open", Schema(["note"], strict=False))


def request(name, value):
    try:
        return {"ok": True, "value": registry.call(name, value)}
    except ValueError:
        return {"ok": False}
