#!/usr/bin/env python3
"""Append one privacy-minimized agent event and update live state."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timezone
from typing import cast

ROOT = pathlib.Path(
    os.environ.get(
        "AGENT_OBSERVABILITY_DIR",
        pathlib.Path.home() / ".local/share/agent-observability",
    )
)
EVENTS = ROOT / "events"
LIVE = ROOT / "live"


def record_event(event: dict[str, object]) -> int:
    now = datetime.now(timezone.utc)
    event.setdefault(
        "ts", now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )
    event.setdefault("schema_version", 2)
    cwd = event.get("cwd")
    if isinstance(cwd, str):
        event["cwd"] = pathlib.Path(cwd).name or "?"
    skill_path = event.pop("skill_path", None)
    if isinstance(skill_path, str):
        with contextlib.suppress(OSError):
            event["skill_version"] = (
                "sha256:"
                + hashlib.sha256(pathlib.Path(skill_path).read_bytes()).hexdigest()
            )

    EVENTS.mkdir(parents=True, exist_ok=True)
    LIVE.mkdir(parents=True, exist_ok=True)

    day = now.date().isoformat()
    with (EVENTS / f"{day}.jsonl").open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(
            json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        handle.flush()
        os.fsync(handle.fileno())

    agent = str(event.get("agent", "unknown"))
    session = str(event.get("session_id", "unknown"))
    live_key = hashlib.sha256(f"{agent}\0{session}".encode()).hexdigest()[:24]
    live_path = LIVE / f"{live_key}.json"
    with (LIVE / f".{live_key}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if event.get("event") == "session_ended":
            live_path.unlink(missing_ok=True)
            return 0

        live: dict[str, object] = {}
        try:
            loaded = json.loads(live_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}
        if isinstance(loaded, dict):
            live = loaded

        if event.get("event") in {"session_started", "agent_started"}:
            live["skills"] = []
        skill = event.get("skill")
        if event.get("event") == "skill_activated" and isinstance(skill, str):
            stored_skills = live.get("skills", [])
            skills = (
                [item for item in stored_skills if isinstance(item, str)]
                if isinstance(stored_skills, list)
                else []
            )
            if not any(item == skill for item in skills):
                skills.append(skill)
            live["skills"] = skills

        for key in ("agent", "session_id", "cwd", "model", "state", "ts"):
            value = event.get(key)
            if value is not None:
                live[key] = value
        live["last_event"] = event.get("event")

        fd, temp_name = tempfile.mkstemp(prefix=".state-", dir=LIVE, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(live, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, live_path)
        finally:
            pathlib.Path(temp_name).unlink(missing_ok=True)
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: record-event.py JSON", file=sys.stderr)
        return 2
    try:
        raw_event = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"invalid event: {exc}", file=sys.stderr)
        return 2
    if not isinstance(raw_event, dict):
        return 2
    return record_event(cast(dict[str, object], raw_event))


if __name__ == "__main__":
    raise SystemExit(main())
