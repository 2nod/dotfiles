#!/usr/bin/env python3
"""Translate Codex hook input into privacy-minimized observability events."""

from __future__ import annotations

import json
import os
import pathlib
import re
import runpy
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
    r"(?:^|\s)(?:pytest|go test|cargo test|npm test|pnpm test|yarn test)(?:\s|$)",
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
        candidates = (
            [text]
            if text.endswith("SKILL.md")
            else [match.group("path") for match in SKILL_PATH.finditer(text)]
        )
        for candidate in candidates:
            path = pathlib.Path(candidate).expanduser()
            if not path.is_absolute():
                path = pathlib.Path(cwd) / path
            path = path.resolve()
            if path.name == "SKILL.md" and str(path) not in seen:
                seen.add(str(path))
                yield path


def number_value(value: Any) -> float:
    try:
        return float(value) if isinstance(value, (int, float)) else 0
    except (TypeError, ValueError):
        return 0


def verification_kind(tool_name: str, tool_input: Any) -> str | None:
    lowered = tool_name.lower()
    if lowered in {"lsp_diagnostics", "lens_diagnostics"}:
        return "diagnostics"
    if any(TEST.search(text) for text in strings(tool_input)):
        return "test"
    if any(BUILD.search(text) for text in strings(tool_input)):
        return "build"
    return None


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
            for path in skill_paths(tool_input, cwd):
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
            details = response.get("details", {}) if isinstance(response, dict) else {}
            diagnostic_count = 0
            if isinstance(details, dict):
                diagnostic_count = sum(
                    number_value(details.get(key))
                    for key in (
                        "totalDiagnostics",
                        "totalBlocking",
                        "totalErrors",
                        "totalWarnings",
                    )
                )
            failed = isinstance(response, dict) and bool(
                response.get("is_error")
                or response.get("isError")
                or (
                    kind == "diagnostics"
                    and (
                        diagnostic_count > 0
                        or details.get("unconfirmed")
                        or details.get("timedOut")
                    )
                )
            )
            emit(
                base,
                event="verification_finished" if kind else "tool_finished",
                tool=tool,
                status="failed" if failed else "passed",
                **({"verification": kind} if kind else {}),
                **({"diagnostics": diagnostic_count} if kind == "diagnostics" else {}),
            )
    elif event == "Stop":
        emit(base, event="agent_end", state="idle")
    elif event == "SessionEnd":
        emit(base, event="session_ended", state="idle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
