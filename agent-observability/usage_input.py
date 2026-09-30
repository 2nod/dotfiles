"""One input selection for CLI analysis and reports; native and legacy never mix."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from usage_events import parse_time
from usage_store import DB_NAME, connect, health

TEXT_FIELDS = (
    "agent", "session_id", "agent_id", "turn_id", "event", "model", "skill",
    "skill_version", "invocation", "verification", "status", "result_evidence",
)


def reconcile(previous, current):
    """Snapshots may precede a result or use an older parser; real conflicts stay visible."""
    if previous.get("parser_version") != current.get("parser_version"):
        return max((previous, current), key=lambda e: e.get("parser_version", 0))
    if previous == current:
        return previous
    kind = current.get("event")
    mutable = {"skill_evidence"} if kind == "skill_activated" else {
        "ts", "status", "result_evidence"} if kind == "verification_finished" else set()
    if {k: v for k, v in previous.items() if k not in mutable} != {k: v for k, v in current.items() if k not in mutable}:
        return None
    if kind == "skill_activated" and {previous.get("skill_evidence"), current.get("skill_evidence")} == {"requested", "confirmed"}:
        return current if current["skill_evidence"] == "confirmed" else previous
    if kind == "verification_finished" and "unknown" in {previous.get("status"), current.get("status")}:
        return current if current.get("status") != "unknown" else previous
    return None


def legacy_events(root, days, now):
    cutoff = now - timedelta(days=days)
    events, errors = [], []
    for path in sorted((root / "events").glob("*.jsonl")):
        try:
            if datetime.strptime(path.stem, "%Y-%m-%d").date() < cutoff.date():
                continue
        except ValueError:
            pass
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            errors.append({"path": str(path), "reason": type(error).__name__})
            continue
        for number, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
            except ValueError:
                event = None
            timestamp = parse_time(event.get("ts")) if isinstance(event, dict) else None
            if not timestamp or not event.get("event") or any(
                event.get(key) is not None and not isinstance(event[key], str) for key in TEXT_FIELDS
            ):
                errors.append({"path": str(path), "line": number, "reason": "invalid event or timestamp"})
                continue
            if cutoff <= timestamp <= now:
                event["_source"] = {"path": str(path), "line": number,
                                    "sha256": hashlib.sha256(line.encode("utf-8")).hexdigest()}
                events.append(event)
    return events, errors


def native_events(root, days, now):
    events, errors, grouped = [], [], {}
    try:
        with closing(connect(root.resolve(), readonly=True)) as db:
            rows = db.execute("""SELECT o.* FROM observations o JOIN files f
                ON f.path=o.path AND f.active=o.generation WHERE o.ts>=? AND o.ts<=?""",
                ((now - timedelta(days=days)).isoformat(), now.isoformat()))
            for row in rows:
                event = json.loads(row["data"])
                refs = json.loads(row["refs"])
                previous = grouped.get(row["id"])
                if previous:
                    merged = reconcile(previous["event"], event)
                    if merged is None:
                        previous["conflict"] = True
                    else:
                        if event.get("parser_version", 0) > previous["event"].get("parser_version", 0):
                            previous["conflict"] = False
                        previous["event"] = merged
                    previous["refs"].extend(refs)
                    previous["ingested"] = max(previous["ingested"], row["ingested"])
                else:
                    grouped[row["id"]] = {"event": event, "refs": refs, "ingested": row["ingested"], "conflict": False}
            for row in db.execute("""SELECT i.path,i.line,i.code FROM issues i JOIN files f
                    ON f.path=i.path AND i.generation=f.generation"""):
                errors.append({"path": row["path"], "line": row["line"], "reason": row["code"]})
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as error:
        return [], [{"path": str(root / DB_NAME), "reason": type(error).__name__}]
    exists = {}
    def call_identity(event):
        return (event.get("agent"), event.get("session_id"), event.get("agent_id"), event.get("tool_use_id"))
    conflicting_calls = {call_identity(item["event"]) for item in grouped.values()
                         if item["conflict"] and item["event"].get("tool_use_id")}
    for eid, item in grouped.items():
        if item["conflict"]:
            errors.append({"event_id": eid, "reason": "conflicting_native_identity"})
            continue
        event = item["event"]
        if event.get("tool_use_id") and call_identity(event) in conflicting_calls:
            continue
        refs = {json.dumps(ref, sort_keys=True): ref for ref in item["refs"]}
        event["_evidence"] = list(refs.values())
        event["_source"] = event["_evidence"][0]
        event["ingested_at"] = item["ingested"]
        for ref in refs.values():
            path = ref["path"]
            if path not in exists:
                exists[path] = Path(path).is_file()
            ref["available"] = exists[path]
        events.append(event)
    return events, errors


def read_usage(root, days=30, now=None, source="auto"):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if source == "auto":
        source = "native" if (root / DB_NAME).exists() else "legacy"
    if source not in {"native", "legacy"}:
        raise ValueError("invalid usage source")
    if source == "native":
        events, errors = native_events(root, days, now)
        collection = health(root, now=now, probe=False)
    else:
        events, errors = legacy_events(root, days, now)
        collection = {"state": "legacy_archive", "last_success": None, "runtimes": []}
    events.sort(key=lambda event: (parse_time(event["ts"]), event.get("native_event_id", "")))
    return {"events": events, "errors": errors, "source": source, "collection": collection}
