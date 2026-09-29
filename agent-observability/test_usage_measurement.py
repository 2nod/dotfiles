"""Observed shell results and actual skill paths must survive hook translation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class UsageMeasurementTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def hook(self, tool, args, response=None):
        payload = {
            "session_id": "session", "turn_id": "turn", "tool_use_id": "call",
            "cwd": str(self.root), "tool_name": tool, "tool_input": args,
            "hook_event_name": "PreToolUse" if response is None else "PostToolUse",
        }
        if response is not None:
            payload["tool_response"] = response
        subprocess.run(
            [sys.executable, str(REPO / "codex/skill-observability.py")],
            input=json.dumps(payload), text=True, check=True,
            env={**os.environ, "AGENT_OBSERVABILITY_DIR": str(self.root),
                 "AGENT_OBSERVABILITY_RECORDER": str(REPO / "agent-observability/record-event.py")},
        )
        return [json.loads(line) for path in (self.root / "events").glob("*.jsonl")
                for line in path.read_text().splitlines()]

    def test_shell_read_records_real_file_version_with_spaces(self):
        skill = self.root / "skills with spaces/demo/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# Synthetic skill\n")
        events = self.hook("Bash", {"command": f'cat "{skill}"'})
        activations = [e for e in events if e["event"] == "skill_activated"]
        self.assertEqual(len(activations), 1)
        self.assertEqual(activations[0]["skill"], "demo")
        self.assertEqual(activations[0]["skill_version"],
                         "sha256:" + hashlib.sha256(skill.read_bytes()).hexdigest())

    def test_missing_files_and_git_or_patch_mentions_are_not_reads(self):
        skill = self.root / "demo/SKILL.md"
        skill.parent.mkdir()
        skill.write_text("# Synthetic skill\n")
        self.hook("Bash", {"command": "cat /missing/example/SKILL.md"})
        self.hook("Bash", {"command": f"git add {skill}"})
        events = self.hook("apply_patch", {"patch": f"*** Update File: {skill}"})
        self.assertFalse(any(e["event"] == "skill_activated" for e in events))

    def test_nonzero_exit_code_is_failed_even_without_tool_error_flag(self):
        events = self.hook("Bash", {"command": "pytest"}, {"exit_code": 1, "output": "private error"})
        self.assertEqual(events[-1]["status"], "failed")
        self.assertEqual(events[-1]["result_evidence"], "exit_code")
        self.assertEqual(events[-1]["tool_use_id"], "call")
        self.assertNotIn("private error", json.dumps(events))

    def test_running_or_missing_exit_status_is_unknown(self):
        events = self.hook("exec_command", {"cmd": "python3 -m unittest discover"}, {"session_id": 12})
        self.assertEqual(events[-1]["event"], "verification_finished")
        self.assertEqual(events[-1]["status"], "unknown")
        self.assertEqual(events[-1]["result_evidence"], "unconfirmed")

    def test_structured_shell_results_and_non_commands(self):
        events = self.hook("Bash", {"command": "pytest"}, json.dumps({"exit_code": 0}))
        self.assertEqual(events[-1]["status"], "passed")
        events = self.hook("write", {"content": "Run pytest before committing"}, {"isError": False})
        self.assertEqual(events[-1]["event"], "tool_finished")

    def test_read_tool_accepts_relative_path_with_spaces(self):
        skill = self.root / "skills with spaces/demo/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# Synthetic skill\n")
        events = self.hook("read", {"path": str(skill.relative_to(self.root))})
        self.assertEqual(events[0]["skill"], "demo")
        self.assertTrue(events[0]["skill_version"].startswith("sha256:"))

    def test_json_diagnostics_keep_counts_and_missing_result_is_unknown(self):
        events = self.hook("lens_diagnostics", {}, json.dumps({"details": {"totalErrors": 2}}))
        self.assertEqual(events[-1]["status"], "failed")
        self.assertEqual(events[-1]["diagnostics"], 2)
        events = self.hook("lens_diagnostics", {}, {"details": {"unconfirmed": True}})
        self.assertEqual(events[-1]["status"], "unknown")

    def test_shell_justification_is_not_a_command(self):
        skill = self.root / "demo/SKILL.md"
        skill.parent.mkdir()
        skill.write_text("# Synthetic skill\n")
        events = self.hook("exec_command", {"cmd": "pwd", "justification": f"cat {skill} then pytest"})
        self.assertEqual([event["event"] for event in events], ["tool_started"])


if __name__ == "__main__":
    unittest.main()
