"""Synthetic transcripts exercise ingestion, recovery and evidence boundaries."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from usage_events import aggregate, build_turns, turn_outcome
from usage_input import read_usage
from usage_native import NativeParser, result_status, tool_metadata
from usage_store import collect, connect, health, ingest_file, source_roots, writer

NOW = datetime(2030, 1, 2, tzinfo=timezone.utc)
TS = "2030-01-01T10:00:00Z"


def codex(kind, payload):
    return {"type": kind, "timestamp": TS, "payload": payload}


def codex_start(session="session-one", turn="turn-one", **extra):
    return [codex("session_meta", {"id": session, "cwd": "/work/project", **extra}),
            codex("turn_context", {"turn_id": turn, "model": "test-model"}),
            codex("event_msg", {"type": "task_started", "turn_id": turn})]


def command(call, cmd, code=0, turn="turn-one"):
    return codex("event_msg", {"type": "item_completed", "turn_id": turn,
        "item": {"type": "CommandExecution", "id": call, "command": ["zsh", "-lc", cmd],
                 "status": "completed", "exit_code": code, "aggregated_output": "PRIVATE_TOOL_OUTPUT"}})


def codex_end(turn="turn-one"):
    return codex("event_msg", {"type": "task_complete", "turn_id": turn})


def claude(role, content, uid, **extra):
    return {"type": role, "uuid": uid, "sessionId": "claude-session", "cwd": "/other/project",
            "timestamp": TS, "message": {"role": role, "content": content, **extra}}


def pi(role, content, uid, parent=None, **extra):
    return {"type": "message", "id": uid, "parentId": parent, "timestamp": TS,
            "message": {"role": role, "content": content, **extra}}


class CollectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "derived"
        self.logs = Path(self.temp.name) / "logs"
        self.logs.mkdir()
        self.roots = {"codex": [str(self.logs)]}

    def write(self, name, rows, mode="w"):
        path = self.logs / name
        with path.open(mode) as stream:
            for row in rows:
                stream.write(json.dumps(row) + "\n")
        return path

    def run_collect(self, **kwargs):
        return collect(self.root, self.roots, **kwargs)

    def read(self, source="native"):
        return read_usage(self.root, now=NOW, source=source)

    def test_native_evidence_idempotence_copies_and_privacy(self):
        rows = codex_start() + [command("read", "cat '/skills/useful skill/SKILL.md'"),
                                command("test", "python3 -m unittest", 0), codex_end()]
        rows.insert(3, codex("response_item", {"type": "message", "role": "user",
                      "content": [{"type": "input_text", "text": "PRIVATE_PROMPT"}]}))
        source = self.write("a.jsonl", rows)
        shutil.copyfile(source, self.logs / "copy.jsonl")
        self.run_collect()
        first = self.read()
        self.assertEqual(first["errors"], [])
        self.run_collect()
        self.assertEqual(first["events"], self.read()["events"])
        turns = build_turns(first["events"])
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].skills, {"useful skill"})
        self.assertEqual(turn_outcome(turns[0]), "検証済み")
        self.assertEqual(aggregate(turns)["useful skill"].uses, 1)
        self.assertFalse(turns[0].versions)
        read = next(e for e in first["events"] if e["event"] == "skill_activated")
        self.assertEqual(len(read["_evidence"]), 2)
        self.assertTrue(all(e["available"] for e in read["_evidence"]))
        with closing(connect(self.root, readonly=True)) as db:
            dump = "\n".join(db.iterdump())
        self.assertNotIn("PRIVATE_PROMPT", dump)
        self.assertNotIn("PRIVATE_TOOL_OUTPUT", dump)
        self.assertNotIn("cat '/skills", dump)
        self.assertEqual((self.root / "usage.sqlite3").stat().st_mode & 0o777, 0o600)

    def test_partial_last_line_bad_middle_and_recovery(self):
        path = self.write("a.jsonl", codex_start())
        tail = json.dumps(command("read", "cat /skills/review/SKILL.md")).encode()
        with path.open("ab") as stream:
            stream.write(b"{invalid}\n" + tail[:50])
        self.run_collect()
        first = self.read()
        self.assertEqual([e["reason"] for e in first["errors"]], ["invalid_json"])
        self.assertEqual(health(self.root)["runtimes"][0]["state"], "awaiting_line")
        self.assertFalse(any(e["event"] == "skill_activated" for e in first["events"]))
        with path.open("ab") as stream:
            stream.write(tail[50:] + b"\n")
        self.run_collect()
        self.assertEqual(len([e for e in self.read()["events"] if e["event"] == "skill_activated"]), 1)
        self.assertEqual(health(self.root)["runtimes"][0]["state"], "up_to_date")
        self.assertEqual(health(self.root)["runtimes"][0]["issues"], {"invalid_json": 1})

    def test_checkpoint_transaction_rolls_back_after_failure(self):
        path = self.write("a.jsonl", codex_start() + [command("read", "cat /skills/review/SKILL.md")])
        def crash():
            raise RuntimeError("simulated process death")
        with self.assertRaises(RuntimeError):
            self.run_collect(before_commit=crash)
        with closing(connect(self.root, readonly=True)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM observations").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM files").fetchone()[0], 0)
        self.run_collect()
        self.assertTrue(build_turns(self.read()["events"])[0].skills)

    def test_replay_generation_is_atomic_and_missing_source_keeps_evidence(self):
        path = self.write("a.jsonl", codex_start() + [command("a", "cat /skills/old/SKILL.md"), codex_end()])
        self.run_collect()
        self.write("a.jsonl", codex_start("new-session") + [command("b", "cat /skills/new/SKILL.md"), codex_end()])
        with writer(self.root) as db:
            ingest_file(db, str(path), "codex", str(self.logs), 1)
        self.assertEqual(build_turns(self.read()["events"])[0].skills, {"old"})
        self.run_collect()
        self.assertEqual(build_turns(self.read()["events"])[0].skills, {"new"})
        path.unlink()
        self.run_collect()
        self.assertEqual(build_turns(self.read()["events"])[0].skills, {"new"})
        self.assertTrue(all(not e["_source"]["available"] for e in self.read()["events"]))
        self.assertEqual(health(self.root)["runtimes"][0]["missing_files"], 1)
        self.assertEqual(health(self.root)["runtimes"][0]["state"], "partial")

    def test_parser_version_replay_and_single_writer(self):
        self.write("a.jsonl", codex_start() + [command("a", "cat /skills/review/SKILL.md")])
        self.run_collect()
        before = self.read()["events"]
        with writer(self.root) as db:
            self.assertEqual(self.run_collect()["state"], "already_running")
            with db:
                db.execute("UPDATE files SET parser=0")
        self.run_collect()
        self.assertEqual([e["native_event_id"] for e in before], [e["native_event_id"] for e in self.read()["events"]])

    def test_claude_late_results_and_model_change(self):
        rows = [claude("user", "PRIVATE_PROMPT", "u1"),
                claude("assistant", [{"type": "tool_use", "id": "read", "name": "Read",
                    "input": {"file_path": "/skills/review/SKILL.md"}}], "a1", model="model-one"),
                claude("user", "next", "u2"),
                claude("assistant", [{"type": "tool_use", "id": "test", "name": "Bash",
                    "input": {"command": "pytest"}}], "a2", model="model-two")]
        path = self.write("a.jsonl", rows)
        self.roots = {"claude-code": [str(self.logs)]}
        self.run_collect()
        self.write("a.jsonl", [claude("user", [{"type": "tool_result", "tool_use_id": "read", "is_error": False,
                                              "content": "PRIVATE_TOOL_OUTPUT"}], "r1"),
            claude("user", [{"type": "tool_result", "tool_use_id": "test", "is_error": False,
                              "content": "All tests passed"}], "r2")], mode="a")
        self.run_collect()
        events = self.read()["events"]
        read = next(e for e in events if e["event"] == "skill_activated")
        self.assertEqual((read["turn_id"], read["model"], read["skill_evidence"]), ("u1", "model-one", "confirmed"))
        test = next(e for e in events if e["event"] == "verification_finished")
        self.assertEqual((test["turn_id"], test["status"]), ("u2", "unknown"))
        self.assertTrue(all(t.turn_id_inferred for t in build_turns(events)))

    def test_claude_structured_file_result_confirms_optional_error_flag(self):
        result = claude("user", [{"type": "tool_result", "tool_use_id": "read", "content": "private"}], "r1")
        result["toolUseResult"] = {"type": "text", "file": {"filePath": "/skills/review/SKILL.md", "content": "private"}}
        self.write("a.jsonl", [claude("user", "start", "u1"), claude("assistant", [{"type": "tool_use", "id": "read",
            "name": "Read", "input": {"file_path": "/skills/review/SKILL.md"}}], "a1"), result])
        self.roots = {"claude-code": [str(self.logs)]}
        self.run_collect()
        self.assertEqual(build_turns(self.read()["events"])[0].skills, {"review"})

    def test_oversized_record_does_not_block_following_activity(self):
        self.write("a.jsonl", codex_start() + [codex("response_item", {"text": "x" * 2000}),
            command("read", "cat /skills/review/SKILL.md"), codex_end()])
        with patch("usage_store.MAX_LINE", 1024):
            self.run_collect()
        self.assertEqual(build_turns(self.read()["events"])[0].skills, {"review"})
        self.assertIn("oversized_record_skipped", [e["reason"] for e in self.read()["errors"]])

    def test_claude_named_skill_structured_success(self):
        result = claude("user", [{"type": "tool_result", "tool_use_id": "skill", "content": "private"}], "r1")
        result["toolUseResult"] = {"success": True, "commandName": "shared:review"}
        self.write("a.jsonl", [claude("user", "start", "u1"), claude("assistant", [{"type": "tool_use", "id": "skill",
            "name": "Skill", "input": {"skill": "shared:review"}}], "a1"), result])
        self.roots = {"claude-code": [str(self.logs)]}
        self.run_collect()
        self.assertEqual(build_turns(self.read()["events"])[0].skills, {"review"})

    def test_copy_with_pending_result_merges_with_finished_original(self):
        call = codex("response_item", {"type": "function_call", "call_id": "read", "name": "exec_command",
                                       "arguments": json.dumps({"cmd": "cat /skills/review/SKILL.md"})})
        self.write("copy.jsonl", codex_start() + [call])
        self.write("original.jsonl", codex_start() + [call, codex("response_item", {
            "type": "function_call_output", "call_id": "read", "output": {"exit_code": 0}})])
        self.run_collect()
        data = self.read()
        self.assertFalse(data["errors"])
        self.assertEqual(aggregate(build_turns(data["events"]))["review"].uses, 1)

    def test_native_report_and_analyzer_use_the_same_input_and_health(self):
        self.write("a.jsonl", codex_start() + [command("read", "cat /skills/review/SKILL.md"), codex_end()])
        self.run_collect()
        def module(name, path):
            spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(path))
            loaded = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(loaded)
            return loaded
        analyzer = module("native_analysis", "analyze-usage.py")
        report = module("native_report", "generate-report.py")
        data = self.read()
        summary = analyzer.analyze(self.root, now=NOW, catalog={"review": {"source": "authored"}})
        turns = build_turns(data["events"])
        page = report.render_overview(30, turns, aggregate(turns), data)
        self.assertEqual(summary["source"], "native")
        self.assertEqual(summary["coverage"]["reviewable_turns"], 1)
        self.assertIn('data-metric="usage-total">1', page)
        self.assertIn("読み込み確認 1件", page)
        self.assertIn("収集確認:", page)
        self.assertEqual(summary["cohorts"][0]["skill_version"], None)

    def test_pi_tree_and_unverified_fork_are_not_new_uses(self):
        rows = [{"type": "session", "id": "pi-session", "timestamp": TS, "cwd": "/work/project"},
                {"type": "model_change", "id": "m1", "provider": "local", "modelId": "one"},
                pi("user", "start", "u1", "m1"),
                pi("assistant", [{"type": "toolCall", "id": "r1", "name": "read",
                                   "arguments": {"path": "/skills/review/SKILL.md"}}], "a1", "u1"),
                pi("user", "other branch", "u2", "m1"),
                pi("toolResult", [{"type": "text", "text": "PRIVATE_OUTPUT"}], "r2", "a1",
                   toolCallId="r1", isError=False),
                pi("assistant", [], "a2", "r2", stopReason="stop")]
        self.write("a.jsonl", rows)
        self.roots = {"pi": [str(self.logs)]}
        self.run_collect()
        turns = build_turns(self.read()["events"])
        used = next(t for t in turns if t.skills)
        self.assertEqual((used.turn_id, used.skills), ("u1", {"review"}))
        rows[0]["parentSession"] = "/old/native.jsonl"
        rows[0]["id"] = "fork-session"
        self.write("fork.jsonl", rows)
        self.run_collect()
        self.assertEqual(aggregate(build_turns(self.read()["events"]))["review"].uses, 1)

    def test_nested_codex_execution_and_false_paths(self):
        rows = codex_start() + [codex("event_msg", {"type": "item_completed", "turn_id": "turn-one",
                                "item": {"type": "UserMessage", "id": "u", "content": []}}),
            codex("response_item", {"type": "custom_tool_call", "name": "exec", "call_id": "wrapper",
                                    "input": "DO_NOT_EXECUTE"}),
            command("read", "sed -n '1,50p' /skills/review/SKILL.md"),
            command("quote", "echo cat /skills/wrong/SKILL.md"),
            command("write", "cat > /skills/write/SKILL.md"),
            command("doc", "python3 - <<'PY'\ncat /skills/data/SKILL.md\nPY"),
            command("sed-data", "sed '/skills/data/SKILL.md' input.txt")]
        self.write("a.jsonl", rows)
        self.run_collect()
        self.assertEqual(build_turns(self.read()["events"])[0].skills, {"review"})

    def test_supported_wrapper_and_unrelated_items_are_not_gaps(self):
        wrapper = codex("response_item", {"type": "custom_tool_call", "name": "exec",
            "call_id": "wrapper", "input": 'text(await tools.exec_command({cmd: "cat /skills/review/SKILL.md"}))'})
        self.write("a.jsonl", codex_start() + [
            codex("response_item", {"type": "custom_tool_call", "name": "apply_patch", "call_id": "patch", "input": "PRIVATE_PATCH"}),
            wrapper, command("read", "cat /skills/review/SKILL.md"),
            codex("response_item", {"type": "custom_tool_call_output", "call_id": "wrapper", "output": []}),
            codex("event_msg", {"type": "item_completed", "turn_id": "turn-one", "item": {
                "type": "FunctionCallOutput", "id": "other", "name": "create_thread", "output": "PRIVATE_OUTPUT"}}), codex_end()])
        self.run_collect()
        self.assertEqual(self.read()["errors"], [])
        self.assertEqual(build_turns(self.read()["events"])[0].skills, {"review"})

    def test_wrapper_without_inner_evidence_stays_visible_across_passes(self):
        self.write("a.jsonl", codex_start() + [codex("response_item", {
            "type": "custom_tool_call", "name": "exec", "call_id": "wrapper", "input": "PRIVATE_JAVASCRIPT"})])
        self.run_collect()
        self.write("a.jsonl", [codex("response_item", {"type": "custom_tool_call_output", "call_id": "wrapper", "output": []})], mode="a")
        self.run_collect()
        self.assertEqual([e["reason"] for e in self.read()["errors"]], ["unsupported_codex_wrapper"])
        runtime = health(self.root)["runtimes"][0]
        self.assertEqual(runtime["state"], "up_to_date")
        self.assertEqual(runtime["issues"], {"unsupported_codex_wrapper": 1})
        # A current file failure must still warn even with the same saved gap.
        with writer(self.root) as db:
            with db:
                db.execute("UPDATE files SET error='OSError'")
        self.assertEqual(health(self.root)["runtimes"][0]["state"], "partial")

    def test_large_compaction_is_ignored_but_large_activity_stays_visible(self):
        self.write("a.jsonl", codex_start() + [
            codex("compacted", {"message": "x" * 2000}),
            codex("response_item", {"type": "custom_tool_call", "input": "x" * 2000}),
            command("read", "cat /skills/review/SKILL.md"), codex_end()])
        with patch("usage_store.MAX_LINE", 1024):
            self.run_collect()
        self.assertEqual([e["reason"] for e in self.read()["errors"]], ["oversized_record_skipped"])
        self.assertEqual(build_turns(self.read()["events"])[0].skills, {"review"})

    def test_analysis_limits_do_not_mean_ingestion_failed(self):
        self.write("a.jsonl", codex_start(forked_from_id="parent") + [command("script", "python3 - <<'PY'\nprint(1)\nPY")])
        self.run_collect()
        runtime = health(self.root)["runtimes"][0]
        self.assertEqual(runtime["state"], "up_to_date")
        self.assertEqual(runtime["limitations"], {"branch_origin_unverified": 1, "unsupported_shell_syntax": 1})
        self.assertEqual(runtime["issues"], {})
        self.assertEqual(self.read()["errors"], [])
        self.assertEqual({row["reason"] for row in self.read()["limitations"]}, set(runtime["limitations"]))

    def test_health_idle_new_source_lag_stopped_missing_and_unconfigured(self):
        self.write("a.jsonl", codex_start())
        self.run_collect()
        current = health(self.root)
        self.assertEqual(current["runtimes"][0]["state"], "up_to_date")
        self.assertEqual(current["runtimes"][1]["state"], "unconfigured")
        self.write("new.jsonl", codex_start("new"))
        self.assertEqual(health(self.root)["runtimes"][0]["state"], "lagging")
        self.assertEqual(health(self.root, now=datetime.now(timezone.utc) + timedelta(minutes=4))["state"], "stopped")
        shutil.rmtree(self.logs)
        self.assertEqual(health(self.root)["runtimes"][0]["state"], "missing")

    def test_native_db_corruption_never_falls_back_to_legacy(self):
        self.root.mkdir()
        (self.root / "events").mkdir()
        (self.root / "events/2030-01-01.jsonl").write_text(json.dumps({"schema_version": 2, "agent": "codex",
            "session_id": "legacy", "event": "agent_started", "ts": TS}) + "\n")
        (self.root / "usage.sqlite3").write_text("broken")
        current = self.read(source="auto")
        self.assertEqual(current["source"], "native")
        self.assertEqual(current["events"], [])
        self.assertEqual(current["collection"]["state"], "unreadable")
        self.assertTrue(current["errors"])
        self.assertEqual(len(self.read(source="legacy")["events"]), 1)

    def test_partial_line_does_not_hide_another_files_backlog(self):
        one = self.write("one.jsonl", codex_start())
        with one.open("ab") as stream:
            stream.write(b'{"type":')
        self.write("two.jsonl", codex_start("second"))
        self.run_collect()
        self.assertEqual(health(self.root)["runtimes"][0]["state"], "awaiting_line")
        self.write("two.jsonl", [command("new", "pytest")], mode="a")
        self.assertEqual(health(self.root)["runtimes"][0]["state"], "lagging")

    def test_conflicting_identity_is_visible_and_not_counted(self):
        self.write("a.jsonl", codex_start() + [command("same", "cat /skills/review/SKILL.md", 0)])
        self.write("b.jsonl", codex_start() + [command("same", "cat /skills/review/SKILL.md", 1)])
        self.run_collect()
        data = self.read()
        self.assertIn("conflicting_native_identity", [e["reason"] for e in data["errors"]])
        self.assertEqual(aggregate(build_turns(data["events"])), {})

    def test_replicated_lifecycle_timestamps_do_not_discard_the_turn(self):
        rows = codex_start() + [command("read", "cat /skills/review/SKILL.md"), codex_end()]
        self.write("a.jsonl", rows)
        copied = json.loads(json.dumps(rows))
        copied[2]["timestamp"] = "2030-01-01T10:00:01Z"
        copied[-1]["timestamp"] = "2030-01-01T10:00:02Z"
        self.write("copy.jsonl", copied)
        self.run_collect()
        data = self.read()
        self.assertEqual(data["errors"], [])
        lifecycle = {e["event"]: e for e in data["events"] if e["event"] in {"agent_started", "agent_end"}}
        self.assertEqual(lifecycle["agent_started"]["ts"], "2030-01-01T10:00:00+00:00")
        self.assertEqual(lifecycle["agent_end"]["ts"], "2030-01-01T10:00:02+00:00")
        self.assertTrue(all(len(e["_evidence"]) == 2 for e in lifecycle.values()))
        self.assertEqual(aggregate(build_turns(data["events"]))["review"].uses, 1)

    def test_replicated_project_conflict_stays_visible_despite_timestamp_difference(self):
        rows = codex_start()
        self.write("a.jsonl", rows)
        rows[0]["payload"]["cwd"] = "/other/project"
        rows[-1]["timestamp"] = "2030-01-01T10:00:01Z"
        self.write("copy.jsonl", rows)
        self.run_collect()
        self.assertIn("conflicting_native_identity", [e["reason"] for e in self.read()["errors"]])

    def test_failed_skill_read_and_compound_test_are_not_success(self):
        self.write("a.jsonl", codex_start() + [command("read", "cat /skills/missing/SKILL.md", 1),
            command("test", "pytest; echo done", 0), codex_end()])
        self.run_collect()
        data = self.read()
        self.assertEqual(aggregate(build_turns(data["events"])), {})
        self.assertEqual(next(e["status"] for e in data["events"] if e["event"] == "verification_finished"), "unknown")

    def test_sources_config_and_dry_run_are_readonly(self):
        config = Path(self.temp.name) / "sources.json"
        config.write_text(json.dumps(self.roots))
        self.assertEqual(source_roots(config)["codex"], [str(self.logs.resolve())])
        spec = importlib.util.spec_from_file_location("collector_cli", Path(__file__).with_name("collect-usage.py"))
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        from unittest.mock import patch
        with patch("sys.argv", ["collect", "--root", str(self.root), "--sources", str(config), "--dry-run"]), patch("builtins.print"):
            self.assertEqual(cli.main(), 0)
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
