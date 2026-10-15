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

from usage_native import ANALYSIS_LIMITATIONS, NativeParser, PARSER_VERSIONS, RUNTIMES

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


def is_compaction_prefix(raw):
    """Identify the outer record type without decoding a huge history payload."""
    prefix = raw.decode("utf-8", errors="replace")
    decoder = json.JSONDecoder()
    offset = len(prefix) - len(prefix.lstrip())
    if prefix[offset:offset + 1] != "{":
        return False
    offset += 1
    try:
        while True:
            offset += len(prefix[offset:]) - len(prefix[offset:].lstrip())
            key, offset = decoder.raw_decode(prefix, offset)
            offset += len(prefix[offset:]) - len(prefix[offset:].lstrip())
            if prefix[offset:offset + 1] != ":":
                return False
            offset += 1
            offset += len(prefix[offset:]) - len(prefix[offset:].lstrip())
            value, offset = decoder.raw_decode(prefix, offset)
            if key == "type":
                return value == "compacted"
            offset += len(prefix[offset:]) - len(prefix[offset:].lstrip())
            if prefix[offset:offset + 1] != ",":
                return False
            offset += 1
    except (ValueError, RecursionError):
        return False


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
                    irrelevant = is_compaction_prefix(raw)
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
                    if not irrelevant:
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


def source_version(row):
    return [row[key] for key in ("active", "generation", "parser", "device", "inode", "size", "mtime")]


def source_is_current(row):
    if row["error"] or not row["active"] or row["active"] != row["generation"]:
        return False
    try:
        stat = Path(row["path"]).stat()
    except OSError:
        return False
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns] == source_version(row)[3:]


def verified_relocation(row, files, relocations):
    saved = relocations.get(row["path"], {})
    target = files.get(saved.get("target"))
    return (target is not None and target["runtime"] == row["runtime"]
            and saved.get("original_version") == source_version(row)
            and saved.get("target_version") == source_version(target)
            and source_is_current(target))


def archive_missing_sources(root, expected, *, reason):
    """Acknowledge an explicitly reviewed snapshot without deleting its evidence."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("a reason for the historical loss is required")
    with writer(root) as db:
        if db is None:
            raise RuntimeError("collector is running; retry after it finishes")
        saved = db.execute("SELECT value FROM meta WHERE key='source_history'").fetchone()
        history = json.loads(saved[0]) if saved else {}
        for path, version in expected.items():
            saved_row = db.execute("SELECT * FROM files WHERE path=?", (path,)).fetchone()
            if saved_row is None or source_version(saved_row) != version:
                raise ValueError("source changed since review")
            try:
                Path(path).stat()
            except FileNotFoundError:
                pass
            else:
                raise ValueError("source is available; collect it instead")
            count = db.execute("SELECT count(*) FROM observations WHERE path=? AND generation=?",
                               (path, saved_row["active"])).fetchone()[0]
            history[path] = {"version": version, "checked": saved_row["checked"],
                             "observations": count, "reason": reason, "archived_at": now_iso()}
        with db:
            db.execute("INSERT OR REPLACE INTO meta VALUES ('source_history',?)", (json.dumps(history),))
    return len(expected)


def reconcile_sources(db, present, deadline):
    """Retain missing sources, but recognize complete observed evidence at a live copy."""
    files = {row["path"]: dict(row) for row in db.execute(
        "SELECT path,runtime,error,active,generation,parser,device,inode,size,mtime FROM files")}
    saved = db.execute("SELECT value FROM meta WHERE key='source_relocations'").fetchone()
    relocations = json.loads(saved[0]) if saved else {}
    candidates = {}
    for path, row in files.items():
        if path in present and source_is_current(row):
            candidates.setdefault((row["runtime"], Path(path).name), []).append(row)

    def observations(row):
        return {r["id"]: (r["data"], sorted((ref["line"], ref["sha256"])
                                          for ref in json.loads(r["refs"])))
                for r in db.execute("SELECT id,data,refs FROM observations WHERE path=? AND generation=?",
                                    (row["path"], row["active"]))}

    for path, row in files.items():
        if time.monotonic() >= deadline:
            break
        if path in present or Path(path).exists() or verified_relocation(row, files, relocations):
            continue
        relocations.pop(path, None)
        options = candidates.get((row["runtime"], Path(path).name), [])
        if not options:
            continue
        original = observations(row)
        if not original:
            continue
        for target in options:
            replacement = observations(target)
            if all(replacement.get(eid) == value for eid, value in original.items()) and source_is_current(target):
                relocations[path] = {"target": target["path"], "original_version": source_version(row),
                                     "target_version": source_version(target)}
                break
    with db:
        db.execute("INSERT OR REPLACE INTO meta VALUES ('source_relocations',?)", (json.dumps(relocations),))
        saved = db.execute("SELECT value FROM meta WHERE key='source_history'").fetchone()
        if saved:
            history = {path: value for path, value in json.loads(saved[0]).items() if path not in present}
            db.execute("INSERT OR REPLACE INTO meta VALUES ('source_history',?)", (json.dumps(history),))


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
        reconcile_sources(db, files, started + max_seconds)
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
            files = [dict(row) for row in db.execute("SELECT path,runtime,size,mtime,device,inode,cursor,active,generation,pending,error,parser,checked FROM files")]
            issues = [dict(row) for row in db.execute("""SELECT f.runtime,i.code,count(*) AS count FROM issues i
                JOIN files f ON f.path=i.path AND i.generation=f.generation GROUP BY f.runtime,i.code""")]
        roots = roots if roots is not None else json.loads(meta.get("roots", "{}"))
        relocations = json.loads(meta.get("source_relocations", "{}"))
        history = json.loads(meta.get("source_history", "{}"))
        by_path = {row["path"]: row for row in files}
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
            limitations = {code: count for code, count in runtime_issues.items() if code in ANALYSIS_LIMITATIONS}
            runtime_issues = {code: count for code, count in runtime_issues.items() if code not in ANALYSIS_LIMITATIONS}
            lag, waiting, missing, pending, errors, replay, relocated, archived = 0, 0, 0, 0, 0, 0, 0, 0
            known = {r["path"] for r in rows}
            new = [p for p, pair in discovered.items() if pair[0] == runtime and p not in known]
            for row in rows:
                try:
                    stat = Path(row["path"]).stat()
                    size = stat.st_size if probe else row["size"]
                except FileNotFoundError:
                    if verified_relocation(row, by_path, relocations):
                        relocated += 1
                        continue
                    reviewed = history.get(row["path"], {})
                    if reviewed.get("version") == source_version(row) and reviewed.get("checked") == row["checked"]:
                        archived += 1
                        continue
                    missing += 1
                    continue
                except OSError:
                    errors += 1
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
                     "partial" if errors or missing else
                     "lagging" if new or replay or lag > waiting else
                     "awaiting_line" if pending else "up_to_date")
            runtimes.append({"runtime": runtime, "state": state, "files": len(rows), "new_files": len(new),
                             "unread_bytes": lag, "missing_files": missing, "relocated_files": relocated,
                             "archived_missing_files": archived, "file_errors": errors,
                             "pending_lines": pending, "replaying_files": replay, "issues": runtime_issues,
                             "limitations": limitations})
        return {"state": "stopped" if stopped else "running", "last_start": meta.get("last_start"),
                "last_success": last, "seconds_since_success": round(age, 1) if age is not None else None,
                "sources": sources, "runtimes": runtimes}
    except (OSError, sqlite3.Error, ValueError, TypeError) as error:
        return {"state": "unreadable", "runtimes": [], "last_success": None,
                "reason": getattr(error, "sqlite_errorname", type(error).__name__),
                "detail": str(error) if isinstance(error, sqlite3.Error) else None}
