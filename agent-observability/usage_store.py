"""Incremental, local-only transcript ingestion and independently readable health."""
from __future__ import annotations

from contextlib import closing, contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

from usage_native import NativeParser, PARSER_VERSIONS, RUNTIMES

DB_NAME = "usage.sqlite3"
MAX_LINE = 16 * 1024 * 1024
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files (
 path TEXT PRIMARY KEY, runtime TEXT NOT NULL, source TEXT NOT NULL,
 device INTEGER, inode INTEGER, size INTEGER DEFAULT 0, mtime INTEGER,
 cursor INTEGER DEFAULT 0, line INTEGER DEFAULT 0,
 head TEXT, boundary TEXT, parser INTEGER, state TEXT DEFAULT '{}',
 active INTEGER DEFAULT 0, generation INTEGER DEFAULT 1,
 checked TEXT, advanced TEXT, error TEXT, pending INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS observations (
 path TEXT, generation INTEGER, id TEXT, ts TEXT, data TEXT, refs TEXT,
 ingested TEXT, PRIMARY KEY (path, generation, id)
);
CREATE INDEX IF NOT EXISTS observations_time ON observations(ts);
CREATE TABLE IF NOT EXISTS issues (
 path TEXT, generation INTEGER, line INTEGER, code TEXT,
 PRIMARY KEY (path, generation, line, code)
);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def default_root():
    return Path(os.environ.get("AGENT_OBSERVABILITY_DIR", Path.home() / ".local/share/agent-observability"))


def source_roots(config=None, home=None):
    home = Path(home or Path.home())
    config = Path(config) if config else home / ".config/agent-observability/sources.json"
    if config.exists():
        raw = json.loads(config.read_text())
        if not isinstance(raw, dict) or any(k not in RUNTIMES or not isinstance(v, list)
                                             or any(not isinstance(p, str) for p in v) for k, v in raw.items()):
            raise ValueError("invalid_sources_config")
    else:
        codex = [home / ".codex", home / "Library/Application Support/orca/codex-runtime-home/home"]
        if os.environ.get("CODEX_HOME"):
            codex.append(Path(os.environ["CODEX_HOME"]))
        codex.extend((home / "Library/Application Support/orca/codex-accounts").glob("*/home"))
        raw = {
            "codex": [str(p / name) for p in codex for name in ("sessions", "archived_sessions")],
            "claude-code": [str(home / ".config/claude/projects"), str(home / ".claude/projects")],
            "pi": [str(home / ".pi/agent/sessions")],
        }
        if os.environ.get("CLAUDE_CONFIG_DIR"):
            raw["claude-code"].append(str(Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects"))
        if os.environ.get("PI_CODING_AGENT_DIR"):
            raw["pi"].append(str(Path(os.environ["PI_CODING_AGENT_DIR"]) / "sessions"))
    return {runtime: sorted({str(Path(p).expanduser().resolve()) for p in raw.get(runtime, [])})
            for runtime in RUNTIMES}


def discover(roots):
    files, sources = {}, []
    for runtime, paths in roots.items():
        for value in paths:
            root = Path(value)
            entry = {"runtime": runtime, "path": value, "state": "missing", "files": 0}
            try:
                if root.is_dir():
                    entry["state"] = "available"
                    for path in root.rglob("*.jsonl"):
                        if path.is_file():
                            files.setdefault(str(path.resolve()), (runtime, value))
                            entry["files"] += 1
            except OSError:
                entry["state"] = "unreadable"
            sources.append(entry)
    return files, sources


def connect(root, *, readonly=False):
    path = Path(root) / DB_NAME
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) if readonly else sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=5000")
    if not readonly:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)
    return db


@contextmanager
def writer(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(root / "collector.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield None
            return
        old_mask = os.umask(0o077)
        try:
            db = connect(root)
            os.chmod(root / DB_NAME, 0o600)
            try:
                yield db
            finally:
                db.close()
        finally:
            os.umask(old_mask)
    finally:
        os.close(fd)


def fingerprints(stream, cursor):
    stream.seek(0)
    head = hashlib.sha256(stream.read(min(cursor, 4096))).hexdigest()
    stream.seek(max(0, cursor - 256))
    boundary = hashlib.sha256(stream.read(min(cursor, 256))).hexdigest()
    return head, boundary


def ingest_file(db, path, runtime, source, budget, *, stamp=None, before_commit=None):
    path = str(Path(path).resolve())
    stamp = stamp or now_iso()
    saved = db.execute("SELECT * FROM files WHERE path=?", (path,)).fetchone()
    with open(path, "rb") as stream:
        stat = os.fstat(stream.fileno())
        prior = dict(saved) if saved else {}
        cursor = prior.get("cursor", 0)
        head, boundary = fingerprints(stream, cursor) if cursor <= stat.st_size else (None, None)
        reset = not saved or any((
            prior.get("device") != stat.st_dev, prior.get("inode") != stat.st_ino,
            cursor > stat.st_size, prior.get("parser") != PARSER_VERSIONS[runtime],
            cursor and (prior.get("head") != head or prior.get("boundary") != boundary),
            stat.st_size == prior.get("size") and stat.st_mtime_ns != prior.get("mtime"),
        ))
        generation = prior.get("generation", 0) + 1 if reset else prior["generation"]
        active = prior.get("active", 0)
        if not reset and cursor == stat.st_size and active == generation:
            with db:
                db.execute("UPDATE files SET checked=?,error=NULL WHERE path=?", (stamp, path))
            return 0
        if reset:
            cursor, line, state = 0, 0, {}
        else:
            line, state = prior["line"], json.loads(prior["state"])
        actor = Path(path).stem if "subagents" in Path(path).parts else "root"
        parser = NativeParser(runtime, state=state, actor=actor)
        start, pending, fatal = cursor, False, None
        stream.seek(cursor)
        # Derived events and the exact checkpoint advance in the same transaction.
        with db:
            if reset and generation != active:
                db.execute("DELETE FROM observations WHERE path=? AND generation<>?", (path, active))
                db.execute("DELETE FROM issues WHERE path=? AND generation<>?", (path, active))
            while cursor < stat.st_size and cursor - start < budget:
                raw = stream.readline(MAX_LINE + 1)
                if not raw:
                    break
                if len(raw) > MAX_LINE:
                    # Large image/output records need not pin the whole session forever.
                    # Drain in bounded chunks; the gap remains explicitly observable.
                    skipped = len(raw)
                    while not raw.endswith(b"\n"):
                        raw = stream.readline(64 * 1024)
                        skipped += len(raw)
                        if not raw:
                            pending = True
                            break
                    if pending:
                        break
                    line += 1
                    cursor += skipped
                    db.execute("INSERT OR IGNORE INTO issues VALUES (?,?,?,?)",
                               (path, generation, line, "oversized_record_skipped"))
                    continue
                if not raw.endswith(b"\n"):
                    pending = True
                    break
                line += 1
                cursor += len(raw)
                ref = {"path": path, "line": line, "sha256": hashlib.sha256(raw.rstrip(b"\r\n")).hexdigest()}
                try:
                    record = json.loads(raw)
                except (ValueError, UnicodeError):
                    events, issues = [], ["invalid_json"]
                else:
                    events, issues = parser.feed(record, ref)
                for eid, event, refs in events:
                    event["parser_version"] = PARSER_VERSIONS[runtime]
                    event["native_event_id"] = eid
                    db.execute("""INSERT INTO observations VALUES (?,?,?,?,?,?,?)
                        ON CONFLICT(path,generation,id) DO UPDATE SET ts=excluded.ts,
                        data=excluded.data,refs=excluded.refs,ingested=excluded.ingested""",
                        (path, generation, eid, event["ts"], json.dumps(event, sort_keys=True), json.dumps(refs), stamp))
                for code in issues:
                    db.execute("INSERT OR IGNORE INTO issues VALUES (?,?,?,?)", (path, generation, line, code))
            if cursor == stat.st_size or pending:
                active = generation
                db.execute("DELETE FROM observations WHERE path=? AND generation<>?", (path, active))
                db.execute("DELETE FROM issues WHERE path=? AND generation<>?", (path, active))
            head, boundary = fingerprints(stream, cursor)
            db.execute("""INSERT OR REPLACE INTO files
                (path,runtime,source,device,inode,size,mtime,cursor,line,head,boundary,parser,state,
                 active,generation,checked,advanced,error,pending) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (path, runtime, source, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns,
                 cursor, line, head, boundary, PARSER_VERSIONS[runtime], json.dumps(parser.snapshot()),
                 active, generation, stamp, stamp if cursor > start else prior.get("advanced"), fatal, pending))
            if before_commit:
                before_commit()
        return cursor - start


def collect(root, roots, *, max_bytes=256 * 1024 * 1024, max_seconds=45, before_commit=None):
    started = time.monotonic()
    with writer(root) as db:
        if db is None:
            return {"state": "already_running"}
        stamp = now_iso()
        with db:
            db.execute("INSERT OR REPLACE INTO meta VALUES ('last_start',?)", (stamp,))
            db.execute("INSERT OR REPLACE INTO meta VALUES ('roots',?)", (json.dumps(roots),))
        files, sources = discover(roots)
        with db:
            db.execute("INSERT OR REPLACE INTO meta VALUES ('sources',?)", (json.dumps(sources),))
        previous = {r["path"]: dict(r) for r in db.execute("SELECT * FROM files")}
        # Fresh appends first; then unvisited/oldest checked backfill. Each file is bounded.
        def priority(path):
            row = previous.get(path, {})
            try:
                append = row.get("active", 0) > 0 and Path(path).stat().st_size > row.get("cursor", 0)
            except OSError:
                append = False
            return (not append, row.get("checked") or "", path)
        total, processed, errors = 0, 0, []
        for path in sorted(files, key=priority):
            if total >= max_bytes or time.monotonic() - started >= max_seconds:
                break
            runtime, source = files[path]
            try:
                total += ingest_file(db, path, runtime, source, min(32 * 1024 * 1024, max_bytes - total),
                                     stamp=stamp, before_commit=before_commit)
                processed += 1
            except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
                code = type(error).__name__
                errors.append({"path": path, "reason": code})
                with db:
                    db.execute("INSERT OR IGNORE INTO files (path,runtime,source) VALUES (?,?,?)", (path,runtime,source))
                    db.execute("UPDATE files SET error=?,checked=? WHERE path=?", (code, stamp, path))
        with db:
            db.execute("INSERT OR REPLACE INTO meta VALUES ('last_success',?)", (now_iso(),))
            db.execute("INSERT OR REPLACE INTO meta VALUES ('last_errors',?)", (json.dumps(errors),))
        return {"state": "partial" if errors else "completed", "files_checked": processed,
                "bytes_read": total, "errors": errors}


def health(root, *, roots=None, now=None, probe=True):
    now = now or datetime.now(timezone.utc)
    if not (Path(root) / DB_NAME).is_file():
        return {"state": "not_started", "runtimes": [], "last_success": None}
    try:
        with closing(connect(Path(root).resolve(), readonly=True)) as db:
            meta = dict(db.execute("SELECT key,value FROM meta"))
            files = [dict(row) for row in db.execute("SELECT path,runtime,size,cursor,active,generation,pending,error,parser FROM files")]
            issues = [dict(row) for row in db.execute("""SELECT f.runtime,i.code,count(*) AS count FROM issues i
                JOIN files f ON f.path=i.path AND i.generation=f.generation GROUP BY f.runtime,i.code""")]
        roots = roots if roots is not None else json.loads(meta.get("roots", "{}"))
        discovered, sources = discover(roots) if probe else ({}, json.loads(meta.get("sources", "[]")))
        last = meta.get("last_success")
        age = (now - datetime.fromisoformat(last)).total_seconds() if last else None
        started = meta.get("last_start")
        start_age = (now - datetime.fromisoformat(started)).total_seconds() if started else None
        stopped = (age is None or age > 180) and (start_age is None or start_age > 180)
        runtimes = []
        for runtime in RUNTIMES:
            rows = [f for f in files if f["runtime"] == runtime]
            source_rows = [s for s in sources if s["runtime"] == runtime]
            runtime_issues = {i["code"]: i["count"] for i in issues if i["runtime"] == runtime}
            lag, waiting, missing, pending, errors, replay = 0, 0, 0, 0, 0, 0
            known = {r["path"] for r in rows}
            new = [p for p, pair in discovered.items() if pair[0] == runtime and p not in known]
            for row in rows:
                try:
                    size = Path(row["path"]).stat().st_size if probe else row["size"]
                except OSError:
                    missing += 1
                    continue
                lag += max(0, size - row["cursor"])
                if row["pending"] and size == row["size"]:
                    waiting += max(0, size - row["cursor"])
                pending += bool(row["pending"])
                errors += bool(row["error"])
                replay += row["active"] != row["generation"] or row["parser"] != PARSER_VERSIONS[runtime]
            for path in new:
                try:
                    lag += Path(path).stat().st_size
                except OSError:
                    missing += 1
            state = ("unconfigured" if not roots.get(runtime) else
                     "missing" if not any(s["state"] == "available" for s in source_rows) else
                     "stopped" if stopped else
                     "partial" if errors or missing or runtime_issues else
                     "lagging" if new or replay or lag > waiting else
                     "awaiting_line" if pending else "up_to_date")
            runtimes.append({"runtime": runtime, "state": state, "files": len(rows), "new_files": len(new),
                             "unread_bytes": lag, "missing_files": missing, "file_errors": errors,
                             "pending_lines": pending, "replaying_files": replay, "issues": runtime_issues})
        return {"state": "stopped" if stopped else "running", "last_start": meta.get("last_start"),
                "last_success": last, "seconds_since_success": round(age, 1) if age is not None else None,
                "sources": sources, "runtimes": runtimes}
    except (OSError, sqlite3.Error, ValueError, TypeError) as error:
        return {"state": "unreadable", "runtimes": [], "last_success": None,
                "reason": getattr(error, "sqlite_errorname", type(error).__name__),
                "detail": str(error) if isinstance(error, sqlite3.Error) else None}
