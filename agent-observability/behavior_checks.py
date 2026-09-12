"""Deterministic checks of isolated Pi tool traces and resulting files."""
import fnmatch
import json
import posixpath


def validate_behavior(spec):
    if not isinstance(spec, dict):
        raise ValueError("behavior must be an object")
    allowed = {"required_reads", "forbidden_reads", "allowed_bash", "required_bash", "files", "unchanged_except"}
    if set(spec) - allowed:
        raise ValueError("unknown behavior checks")
    for key in allowed - {"files"}:
        if key in spec and (not isinstance(spec[key], list) or any(not isinstance(v, str) for v in spec[key])):
            raise ValueError("behavior." + key + " must be a string list")
    if "files" in spec and (not isinstance(spec["files"], dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in spec["files"].items())):
        raise ValueError("behavior.files must map paths to expected text")


def check_behavior(spec, output, before, after):
    validate_behavior(spec)
    calls, completed = [], {}
    errors = []
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "tool_execution_start":
            if not isinstance(event.get("args"), dict) or not event.get("toolCallId"):
                errors.append("tool trace is missing arguments or call id")
            else:
                calls.append(event)
        elif event.get("type") == "tool_execution_end":
            completed[event.get("toolCallId")] = event
    if before != after and not calls:
        errors.append("changed files without observable tool trace")
    reads, commands, successful_commands = [], [], []
    for call in calls:
        name, args = call.get("toolName"), call["args"]
        if name == "read":
            raw = args.get("path", "")
            reads.append(posixpath.normpath(raw if raw.startswith("/") else "/workspace/" + raw))
        elif name == "bash":
            command = args.get("command", "")
            commands.append(command)
            end = completed.get(call["toolCallId"], {})
            result = end.get("result", {})
            if end.get("isError") is False and isinstance(result, dict) and not result.get("isError", False):
                successful_commands.append(command)
        elif name not in ("write", "edit"):
            errors.append("unsupported tool prevents behavior verification: " + str(name))
    # Shell access can hide reads, so reading constraints require an explicit command allowlist.
    if "required_reads" in spec or "forbidden_reads" in spec:
        for command in commands:
            if command not in spec.get("allowed_bash", []):
                errors.append("unobserved shell access: " + command)
    for pattern in spec.get("required_reads", []):
        if not any(fnmatch.fnmatchcase(path, pattern) for path in reads):
            errors.append("required read missing: " + pattern)
    for pattern in spec.get("forbidden_reads", []):
        if any(fnmatch.fnmatchcase(path, pattern) for path in reads):
            errors.append("unnecessary read: " + pattern)
    for command in spec.get("required_bash", []):
        if command not in successful_commands:
            errors.append("successful verification missing: " + command)
    for path, expected in spec.get("files", {}).items():
        if after.get(path) != expected.encode():
            errors.append("completion mismatch: " + path)
    if "unchanged_except" in spec:
        for path in before.keys() | after.keys():
            if path not in spec["unchanged_except"] and before.get(path) != after.get(path):
                errors.append("unexpected change: " + path)
    return {"passed": not errors, "errors": errors, "reads": reads,
            "commands": commands, "successful_commands": successful_commands}
