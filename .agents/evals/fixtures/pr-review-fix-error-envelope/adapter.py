import re

KINDS = {"STALE_VERSION": "conflict", "IN_PROGRESS": "busy", "NO_DOCUMENT": "not_found"}


def to_error(error):
    match = re.match(r"^([A-Z][A-Z_]+)(?::|$)", str(error))
    code = match[1] if match else "OPERATION_FAILED"
    kind = KINDS.get(code, "unavailable")
    return {"code": code, "kind": kind, "retryable": kind in {"busy", "unavailable"}}
