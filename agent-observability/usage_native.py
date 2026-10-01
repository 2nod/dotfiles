"""Read native transcripts as data; retain only activity metadata and evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import posixpath
import re
import shlex

PARSER_VERSIONS = {"codex": 3, "claude-code": 3, "pi": 2}
# These retain evidence of an analysis boundary, not a failed log read.
ANALYSIS_LIMITATIONS = {"branch_origin_unverified", "unsupported_shell_syntax"}
RUNTIMES = ("codex", "claude-code", "pi")
READ_TOOLS = {"read", "read_file", "read_text_file"}
SHELL_TOOLS = {"bash", "shell", "shell_command", "exec_command", "commandexecution"}
TEST_PREFIXES = (("pytest",), ("go", "test"), ("cargo", "test"),
                 ("npm", "test"), ("pnpm", "test"), ("yarn", "test"))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def timestamp(value):
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value / 1000, timezone.utc)
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat() if dt.tzinfo else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def text_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(x.get("text", "")) for x in content
                         if isinstance(x, dict) and x.get("type") in {"text", "input_text"})
    return ""


def shell_parts(command):
    """Lex simple commands without expanding variables or running shell input."""
    if isinstance(command, list):
        if len(command) >= 3 and posixpath.basename(str(command[0])) in {"bash", "sh", "zsh", "fish"} and "c" in str(command[1]):
            command = command[2]
        else:
            command = shlex.join(str(x) for x in command)
    if not isinstance(command, str) or "$(" in command or "`" in command:
        return [], False
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return [], False
    # A here-document is program/data input, not a series of shell commands.
    if any("<<" in t for t in tokens):
        return [], False
    parts, part = [], []
    for token in tokens:
        if token and all(ch in ";&|()\n" for ch in token):
            if part:
                parts.append(part)
                part = []
        else:
            part.append(token)
    if part:
        parts.append(part)
    for part in parts:
        while part and re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", part[0]):
            part.pop(0)
    parts = [p for p in parts if p]
    return parts, len(parts) == 1 and not any(t in {"<", ">", ">>", "&"} for t in tokens)


def skill_from_path(path, project_id):
    if not isinstance(path, str) or any(c in path for c in "$*?\n"):
        return None
    clean = posixpath.normpath(path.replace("\\", "/"))
    if posixpath.basename(clean) != "SKILL.md":
        return None
    name = posixpath.basename(posixpath.dirname(clean))
    if not name or name in {".", ".."}:
        return None
    identity = clean if clean.startswith(("/", "~/")) else [project_id, clean]
    return {"skill": name, "skill_id": digest(identity), "invocation": "read"}


def tool_metadata(name, args, project_id):
    name = name.lower().split(".")[-1]
    args = args if isinstance(args, dict) else {}
    skills, verification, simple = [], None, True
    unsupported = False
    if name in READ_TOOLS:
        skill = skill_from_path(args.get("path", args.get("file_path", args.get("filename"))), project_id)
        if skill:
            skills.append(skill)
    elif name == "skill":
        skill = args.get("skill", args.get("name"))
        if isinstance(skill, str) and re.fullmatch(r"[\w:./-]+", skill):
            skills.append({"skill": skill.rsplit(":", 1)[-1], "skill_id": digest(["named", skill]), "invocation": "explicit"})
    elif name in SHELL_TOOLS:
        parts, simple = shell_parts(args.get("command", args.get("cmd")))
        unsupported = not bool(parts)
        for part in parts:
            executable = posixpath.basename(part[0])
            if executable in {"cat", "head", "tail", "sed", "bat"} and not any(
                "<" in t or ">" in t for t in part[1:]
            ):
                operands = part[1:]
                if executable == "sed":
                    # Only the common `sed [-n] SCRIPT FILE...` form is observed.
                    # Never treat a sed expression or -f script as a file read.
                    operands = operands[1:] if operands[:1] == ["-n"] else operands
                    operands = operands[1:] if operands and not operands[0].startswith("-") else []
                for token in operands:
                    skill = skill_from_path(token, project_id)
                    if skill and skill not in skills:
                        skills.append(skill)
            command = [executable, *part[1:]]
            if any(tuple(command[:len(prefix)]) == prefix for prefix in TEST_PREFIXES) or (
                re.fullmatch(r"python(?:3(?:\.\d+)?)?", executable)
                and command[1:3] in [["-m", "pytest"], ["-m", "unittest"]]
            ):
                verification = "test"
            elif command[:2] in [["nix", "build"], ["nix", "flake"]]:
                if command[:2] == ["nix", "build"] or command[:3] == ["nix", "flake", "check"]:
                    verification = "build"
    elif name in {"lsp_diagnostics", "lens_diagnostics"}:
        verification = "diagnostics"
    return {"tool": name, "skills": skills, "verification": verification,
            "simple": simple, "unsupported": unsupported}


def result_status(result, verification=None, simple=True):
    if not isinstance(result, dict):
        return "unknown", "unconfirmed"
    if verification and not simple:
        return "unknown", "unconfirmed"
    details = result.get("details")
    details = details if isinstance(details, dict) else result
    if result.get("is_error") is True or result.get("isError") is True:
        return "failed", "error_flag"
    for obj in (result, details):
        for key in ("exit_code", "exitCode"):
            if type(obj.get(key)) is int:
                return ("failed" if obj[key] else "passed"), "exit_code"
    if verification == "diagnostics":
        if details.get("unconfirmed"):
            return "unknown", "unconfirmed"
        if details.get("timedOut"):
            return "failed", "diagnostics"
        if any(key in details for key in ("totalErrors", "totalBlocking", "diagnostics")):
            counts = [details.get(key, 0) or 0 for key in ("totalErrors", "totalBlocking")]
            diagnostics = details.get("diagnostics", [])
            if any(type(n) is not int for n in counts) or not isinstance(diagnostics, list):
                return "unknown", "unconfirmed"
            errors = max(counts) + sum(isinstance(d, dict) and d.get("severity") in (1, "error", "Error")
                                      for d in diagnostics)
            return ("failed" if errors else "passed"), "diagnostics"
    return "unknown", "unconfirmed"


class NativeParser:
    def __init__(self, runtime, state=None, actor="root"):
        self.runtime = runtime
        self.state = state or {"actor": actor}
        self.state.setdefault("calls", {})
        self.closed = set(self.state.pop("closed_calls", []))
        self.events = []
        self.issues = []

    def snapshot(self):
        return {**self.state, "closed_calls": sorted(self.closed)}

    def issue(self, code):
        self.issues.append(code)

    def context(self, row, turn=None):
        tid = turn or self.state.get("turn")
        meta = self.state.get("turns", {}).get(tid, {})
        base = {"schema_version": 3, "agent": self.runtime,
                "session_id": self.state.get("session"), "agent_id": self.state.get("actor", "root"),
                "turn_id": tid, "turn_id_inferred": self.runtime != "codex",
                "ts": timestamp(row.get("timestamp")),
                "cwd": meta.get("project", self.state.get("project", "?")),
                "project_id": meta.get("project_id", self.state.get("project_id", ""))}
        model = meta.get("model", self.state.get("model"))
        if model:
            base["model"] = model
        if self.state.get("branch_unverified"):
            base["branch_unverified"] = True
        return base

    def set_project(self, path):
        if isinstance(path, str):
            self.state["project"] = posixpath.basename(path.rstrip("/")) or "?"
            self.state["project_id"] = digest(path)

    def emit(self, base, key, event, refs, **fields):
        if not base.get("session_id") or not base.get("turn_id") or not base.get("ts"):
            self.issue("missing_identity_or_timestamp")
            return
        record = {**base, "event": event, **fields}
        eid = digest([self.runtime, base["session_id"], base["agent_id"], key, event, fields.get("skill_id")])
        self.events.append((eid, record, refs))

    def start(self, base, name, args, call_id, ref):
        if not call_id or call_id in self.closed or call_id in self.state["calls"]:
            return
        info = tool_metadata(name, args, base.get("project_id"))
        if info["unsupported"]:
            self.issue("unsupported_shell_syntax")
        call = {**info, "base": base, "ref": ref}
        self.state["calls"][call_id] = call
        common = {"tool": info["tool"], "tool_use_id": call_id}
        self.emit(base, call_id, "verification_started" if info["verification"] else "tool_started", [ref],
                  **common, **({"verification": info["verification"]} if info["verification"] else {}))
        for skill in info["skills"]:
            self.emit(base, call_id, "skill_activated", [ref], **skill, **common, skill_evidence="requested")
        if info["verification"]:
            self.emit(base, call_id, "verification_finished", [ref], **common,
                      verification=info["verification"], status="unknown", result_evidence="unconfirmed")

    def finish(self, call_id, result, row, ref, *, read_success=False):
        call = self.state["calls"].pop(call_id, None)
        if not call:
            return
        self.closed.add(call_id)
        base, info = call["base"], call
        result_base = {**base, "ts": timestamp(row.get("timestamp")) or base.get("ts")}
        refs = [call["ref"]] if ref == call["ref"] else [call["ref"], ref]
        status, evidence = result_status(result, info["verification"], info["simple"])
        common = {"tool": info["tool"], "tool_use_id": call_id}
        if info["verification"]:
            self.emit(result_base, call_id, "verification_finished", refs, **common,
                      verification=info["verification"], status=status, result_evidence=evidence)
        else:
            self.emit(result_base, call_id, "tool_finished", refs, **common, status=status, result_evidence=evidence)
        confirmed = info["simple"] and (status == "passed" or (
            read_success and info["tool"] in READ_TOOLS | {"skill"} and status != "failed"))
        for skill in info["skills"]:
            self.emit(base, call_id, "skill_activated", refs, **skill, **common,
                      skill_evidence="confirmed" if confirmed else "requested")

    def explicit(self, base, content, key, ref):
        for name in sorted(set(re.findall(r"(?<![\w$])\$([a-z][a-z0-9]*(?:-[a-z0-9]+)*)\b", text_content(content)))):
            self.emit(base, key, "skill_activated", [ref], skill=name,
                      skill_id=digest(["named", name]), invocation="explicit", skill_evidence="explicit")

    def feed(self, row, ref):
        self.events, self.issues = [], []
        if not isinstance(row, dict):
            return [], ["invalid_record"]
        payload = row.get("payload", {})
        message = row.get("message", {})
        if not isinstance(payload, dict) or not isinstance(message, dict):
            return [], ["invalid_record_shape"]
        item = payload.get("item", {})
        if not isinstance(item, dict):
            return [], ["invalid_record_shape"]
        for obj in (row, payload, message, item):
            for key in ("id", "type", "role", "sessionId", "agentId", "promptId", "uuid", "parentId",
                        "turn_id", "call_id", "name", "tool", "tool_name", "toolCallId", "model", "modelId"):
                if obj.get(key) is not None and not isinstance(obj[key], str):
                    return [], ["invalid_record_shape"]
        getattr(self, self.runtime.replace("-", "_"))(row, ref)
        return self.events, self.issues

    def codex(self, row, ref):
        kind, payload = row.get("type"), row.get("payload", {})
        if not isinstance(payload, dict):
            self.issue("invalid_payload")
            return
        if kind == "session_meta":
            self.state["session"] = payload.get("id", payload.get("session_id"))
            self.set_project(payload.get("cwd"))
            if payload.get("forked_from_id") or payload.get("forked_from"):
                self.state["branch_unverified"] = True
                self.issue("branch_origin_unverified")
        elif kind == "turn_context":
            turn = payload.get("turn_id")
            if not turn:
                return
            self.state["turn"] = turn
            self.set_project(payload.get("cwd"))
            self.state.setdefault("turns", {})[turn] = {
                "model": payload.get("model"), "project": self.state.get("project"),
                "project_id": self.state.get("project_id")}
        elif kind == "event_msg":
            event = payload.get("type")
            turn = payload.get("turn_id", self.state.get("turn"))
            base = self.context(row, turn)
            if event == "task_started":
                self.state["turn"] = turn
                self.emit(base, turn, "agent_started", [ref])
            elif event in {"task_complete", "task_aborted"}:
                self.emit(base, turn, "agent_end", [ref])
            elif event == "item_completed":
                self.state["item_history"] = True
                item = payload.get("item", {})
                itype, iid = item.get("type"), item.get("id")
                if itype == "CommandExecution":
                    for wrapper in self.state.get("wrappers", {}).values():
                        wrapper["inner_execution"] = True
                    start = {**base, "ts": timestamp(payload.get("started_at_ms")) or base.get("ts")}
                    self.start(start, "exec_command", {"command": item.get("command")}, iid, ref)
                    if item.get("status") in {"completed", "failed", "declined"} or type(item.get("exit_code")) is int:
                        self.finish(iid, item, row, ref)
                elif itype == "UserMessage":
                    self.explicit(base, item.get("content"), iid, ref)
                elif itype in {"McpToolCall", "DynamicToolCall"}:
                    name = item.get("tool", item.get("tool_name", "unknown"))
                    self.start(base, name, item.get("arguments", {}), iid, ref)
                    result = item.get("result", {})
                    self.finish(iid, result if isinstance(result, dict) else {}, row, ref)
                elif itype == "FunctionCallOutput":
                    # A standalone result has no input to infer a skill read from.
                    result = item.get("output", {})
                    self.finish(iid, result if isinstance(result, dict) else {}, row, ref)
                elif itype not in {"AgentMessage", "Reasoning", "FileChange", "ContextCompaction", "Extension", "Plan", "WebSearch", "ImageView", "CollabAgentToolCall", "EnteredReviewMode", "ExitedReviewMode", "HookPrompt", "SubAgentActivity"}:
                    self.issue("unsupported_codex_item")
        elif kind == "response_item":
            base = self.context(row)
            itype, call = payload.get("type"), payload.get("call_id")
            if itype == "custom_tool_call_output":
                wrapper = self.state.get("wrappers", {}).pop(call, None)
                if wrapper and not wrapper["inner_execution"]:
                    self.issue("unsupported_codex_wrapper")
                return
            if self.state.get("item_history"):
                return
            if itype == "function_call":
                name = payload.get("name", "unknown")
                try:
                    args = json.loads(payload.get("arguments", "{}"))
                except (ValueError, TypeError):
                    args = {}
                self.start(base, name, args, call, ref)
            elif itype == "function_call_output":
                result = payload.get("output", {})
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except ValueError:
                        result = {}
                self.finish(call, result, row, ref)
            elif itype == "custom_tool_call":
                # Patch input is unrelated to reads/tests; never parse or execute it.
                if payload.get("name", "").split(".")[-1] != "apply_patch" and call:
                    self.state.setdefault("wrappers", {})[call] = {"inner_execution": False}

    def claude_code(self, row, ref):
        if row.get("sessionId"):
            self.state["session"] = row["sessionId"]
        self.set_project(row.get("cwd"))
        if row.get("agentId"):
            self.state["actor"] = row["agentId"]
        message = row.get("message", {})
        if not isinstance(message, dict):
            return
        content = message.get("content", [])
        blocks = content if isinstance(content, list) else []
        role = message.get("role", row.get("type"))
        key = row.get("uuid", message.get("id"))
        results = [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_result"]
        if role == "user" and not results and not row.get("isMeta"):
            turn = row.get("promptId") or key
            self.state["turn"] = turn
            self.state.pop("model", None)
            base = self.context(row)
            self.emit(base, turn, "agent_started", [ref])
            self.explicit(base, content, key, ref)
        if role == "assistant":
            if message.get("model"):
                self.state["model"] = message["model"]
            base = self.context(row)
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    self.start(base, block.get("name", "unknown"), block.get("input", {}), block.get("id"), ref)
            if message.get("stop_reason") in {"end_turn", "stop_sequence"}:
                self.emit(base, self.state.get("turn"), "agent_end", [ref])
        for result in results:
            structured = row.get("toolUseResult", {})
            merged = {**(structured if isinstance(structured, dict) else {}), **result}
            file_result = structured.get("file") if isinstance(structured, dict) else None
            read_result = (isinstance(file_result, dict) and isinstance(file_result.get("content"), str)
                           and isinstance(file_result.get("filePath"), str))
            skill_result = isinstance(structured, dict) and structured.get("success") is True
            self.finish(result.get("tool_use_id"), merged, row, ref,
                        read_success=result.get("is_error") is False or read_result or skill_result)

    def pi(self, row, ref):
        kind = row.get("type")
        if kind == "session":
            self.state["session"] = row.get("id")
            self.set_project(row.get("cwd"))
            if row.get("parentSession"):
                self.state["branch_unverified"] = True
                self.issue("branch_origin_unverified")
            return
        parent = self.state.setdefault("nodes", {}).get(row.get("parentId"))
        if parent:
            self.state["turn"], self.state["model"] = parent
        if kind == "model_change":
            self.state["model"] = "/".join(str(row.get(k, "?")) for k in ("provider", "modelId"))
        if kind == "message":
            message = row.get("message", {})
            if not isinstance(message, dict):
                return
            role = message.get("role")
            if role == "user":
                self.state["turn"] = row.get("id")
                base = self.context(row)
                self.emit(base, row.get("id"), "agent_started", [ref])
                self.explicit(base, message.get("content"), row.get("id"), ref)
            elif role == "assistant":
                if message.get("model"):
                    self.state["model"] = "/".join(str(message.get(k, "?")) for k in ("provider", "model"))
                base = self.context(row)
                for block in message.get("content", []) if isinstance(message.get("content"), list) else []:
                    if isinstance(block, dict) and block.get("type") == "toolCall":
                        self.start(base, block.get("name", "unknown"), block.get("arguments", {}), block.get("id"), ref)
                if message.get("stopReason") == "stop":
                    self.emit(base, self.state.get("turn"), "agent_end", [ref])
            elif role == "toolResult":
                self.finish(message.get("toolCallId"), message, row, ref,
                            read_success=message.get("isError") is False)
        if row.get("id"):
            self.state["nodes"][row["id"]] = [self.state.get("turn"), self.state.get("model")]
