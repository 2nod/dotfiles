#!/usr/bin/env python3
"""Translate Codex hook input into privacy-minimized observability events."""

from __future__ import annotations

import json
import os
import pathlib
import re
import runpy
import shlex
import sys
from collections.abc import Callable
from typing import Any, cast

RECORDER = os.environ.get("AGENT_OBSERVABILITY_RECORDER") or str(
    pathlib.Path.home() / ".local/bin/agent-observability-record"
)


def load_recorder() -> Callable[[dict[str, object]], int] | None:
    if not RECORDER or not pathlib.Path(RECORDER).is_file():
        return None
    try:
        namespace = runpy.run_path(RECORDER)
    except (ImportError, OSError, SyntaxError):
        return None
    recorder = namespace.get("record_event")
    return (
        cast(Callable[[dict[str, object]], int], recorder)
        if callable(recorder)
        else None
    )


RECORD_EVENT = load_recorder()
SKILL_PATH = re.compile(r"(?P<path>(?:~|/|\.{0,2}/)[^\s'\"]*?/([^/\s'\"]+)/SKILL\.md)")
TEST = re.compile(
    r"(?:^|\s)(?:pytest|python(?:3(?:\.\d+)?)? -m (?:pytest|unittest)|go test|cargo test|npm test|pnpm test|yarn test)(?:\s|$)",
    re.I,
)
BUILD = re.compile(r"(?:^|\s)(?:nix build|nix flake check)(?:\s|$)", re.I)


def strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def skill_paths(tool_input: Any, cwd: str):
    seen: set[str] = set()
    for text in strings(tool_input):
        # An entire `cat .../SKILL.md` command is not a path. Tokenization also
        # preserves quoted paths containing spaces without executing the shell.
        candidates = [text]
        try:
            candidates.extend(shlex.split(text))
        except ValueError:
            pass
        candidates.extend(match.group("path") for match in SKILL_PATH.finditer(text))
        for candidate in candidates:
            if not candidate.endswith("SKILL.md"):
                continue
            path = pathlib.Path(candidate).expanduser()
            if not path.is_absolute():
                path = pathlib.Path(cwd) / path
            try:
                path = path.resolve()
                exists = path.is_file()
            except (OSError, RuntimeError, ValueError):
                continue
            if path.name == "SKILL.md" and exists and str(path) not in seen:
                seen.add(str(path))
                yield path


def skill_read_input(tool_name: str, tool_input: Any):
    """Recognize reads, not skill paths mentioned in patches or git commands."""
    if tool_name.lower() in {"read", "read_file", "read_text_file"}:
        return tool_input
    if tool_name.lower() in {"bash", "shell", "shell_command", "exec_command"}:
        return [
            match.group(0)
            for text in shell_commands(tool_input)
            for match in re.finditer(r"(?:^|[\n;&|])\s*(?:cat|head|tail|sed|bat)\s+[^\n;&|]+", text)
        ]
    return []


def shell_commands(tool_input: Any):
    if isinstance(tool_input, str):
        yield tool_input
    elif isinstance(tool_input, dict):
        for key in ("command", "cmd"):
            if isinstance(tool_input.get(key), str):
                yield tool_input[key]


def number_value(value: Any) -> float:
    try:
        return float(value) if isinstance(value, (int, float)) else 0
    except (TypeError, ValueError):
        return 0


def diagnostic_counts(details: Any) -> tuple[float, float]:
    if not isinstance(details, dict):
        return 0, 0
    errors = max(
        number_value(details.get("totalBlocking")),
        number_value(details.get("totalErrors")),
    )
    diagnostics = details.get("diagnostics", [])
    if isinstance(diagnostics, list):
        errors = max(
            errors,
            sum(
                isinstance(item, dict) and item.get("severity") in {1, "error", "Error"}
                for item in diagnostics
            ),
        )
    if details.get("severity") == "error":
        errors = max(errors, number_value(details.get("totalDiagnostics")))
    return errors, number_value(details.get("totalWarnings"))


def verification_kind(tool_name: str, tool_input: Any) -> str | None:
    lowered = tool_name.lower()
    if lowered in {"lsp_diagnostics", "lens_diagnostics"}:
        return "diagnostics"
    if lowered not in {"bash", "shell", "shell_command", "exec_command"}:
        return None
    if any(TEST.search(text) for text in shell_commands(tool_input)):
        return "test"
    if any(BUILD.search(text) for text in shell_commands(tool_input)):
        return "build"
    return None


def result_status(response: Any, kind: str | None) -> tuple[str, str]:
    """Only terminal evidence can prove that a shell verification succeeded."""
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except ValueError:
            return "unknown", "unconfirmed"
    if not isinstance(response, dict):
        return "unknown", "unconfirmed"
    details = response.get("details", {})
    details = details if isinstance(details, dict) else {}
    if response.get("is_error") or response.get("isError"):
        return "failed", "error_flag"
    if kind == "diagnostics":
        errors, _ = diagnostic_counts(details)
        if errors > 0 or details.get("timedOut"):
            return "failed", "diagnostics"
        if details.get("unconfirmed") or not any(
            key in details for key in ("totalBlocking", "totalErrors", "totalWarnings", "diagnostics", "totalDiagnostics")
        ):
            return "unknown", "unconfirmed"
        return "passed", "diagnostics"
    codes = [
        obj[key]
        for obj in (response, details)
        for key in ("exit_code", "exitCode")
        if type(obj.get(key)) is int
    ]
    if codes:
        return ("failed" if any(codes) else "passed"), "exit_code"
    if kind:
        return "unknown", "unconfirmed"
    return "passed", "tool_response"


def emit(base: dict[str, Any], **fields: Any) -> None:
    if not RECORD_EVENT:
        return
    payload: dict[str, object] = {**base, **fields}
    try:
        RECORD_EVENT(payload)
    except (OSError, TypeError, ValueError):
        return


def main() -> int:
    try:
        hook = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(hook, dict):
        return 0

    event = str(hook.get("hook_event_name", ""))
    cwd = str(hook.get("cwd", ""))
    base: dict[str, Any] = {
        "agent": "codex",
        "session_id": str(hook.get("session_id", "unknown")),
        "cwd": cwd,
    }
    for key in ("turn_id", "model", "agent_id", "agent_type"):
        if hook.get(key):
            base[key] = hook[key]
    if hook.get("tool_use_id"):
        base["tool_use_id"] = hook["tool_use_id"]

    if event == "SessionStart":
        emit(base, event="session_started", state="idle")
    elif event == "UserPromptSubmit":
        emit(base, event="agent_started", state="working")
        prompt = str(hook.get("prompt", ""))
        for skill in dict.fromkeys(re.findall(r"\$([a-z0-9][a-z0-9-]*)", prompt, re.I)):
            emit(
                base,
                event="skill_activated",
                skill=skill.lower(),
                invocation="explicit",
            )
    elif event in {"PreToolUse", "PostToolUse"}:
        tool = str(hook.get("tool_name", "unknown"))
        tool_input = hook.get("tool_input", {})
        kind = verification_kind(tool, tool_input)
        if event == "PreToolUse":
            for path in skill_paths(skill_read_input(tool, tool_input), cwd):
                emit(
                    base,
                    event="skill_activated",
                    skill=path.parent.name,
                    skill_path=str(path),
                    invocation="read",
                )
            emit(
                base,
                event="verification_started" if kind else "tool_started",
                tool=tool,
                **({"verification": kind} if kind else {}),
            )
        else:
            response = hook.get("tool_response")
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except ValueError:
                    pass
            details = response.get("details", {}) if isinstance(response, dict) else {}
            if not isinstance(details, dict):
                details = {}
            diagnostic_count, warning_count = diagnostic_counts(details)
            status, evidence = result_status(response, kind)
            emit(
                base,
                event="verification_finished" if kind else "tool_finished",
                tool=tool,
                status=status,
                result_evidence=evidence,
                **({"verification": kind} if kind else {}),
                **(
                    {"diagnostics": diagnostic_count, "warnings": warning_count}
                    if kind == "diagnostics"
                    else {}
                ),
            )
    elif event == "Stop":
        emit(base, event="agent_end", state="idle")
    elif event == "SessionEnd":
        emit(base, event="session_ended", state="idle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
