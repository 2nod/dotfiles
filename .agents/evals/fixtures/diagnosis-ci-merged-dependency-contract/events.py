import json

from schema_api import record


def parse_event(raw, fallback_type):
    try:
        data = record(object).parse(json.loads(raw))
        return {**data, "type": data.get("type", fallback_type)}
    except (TypeError, ValueError):
        if fallback_type == "message":
            return None
        return {"type": fallback_type, "text": raw}
