#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
RECORDER = REPO / "agent-observability/record-event.py"
REPORTER = REPO / "agent-observability/generate-report.py"
EVALUATOR = REPO / "agent-observability/evaluate-skill.py"
AUDITOR = REPO / "agent-observability/audit-evals.py"
CODEX = REPO / "codex/skill-observability.py"
EVAL_CASE = REPO / ".agents/evals/ponytail-cache.json"
EVAL_FIXTURE = REPO / ".agents/evals/fixtures/ponytail-cache"
EVAL_VERIFIER = REPO / ".agents/evals/ponytail-cache-verify.py"


class ObservabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.env = {**os.environ, "AGENT_OBSERVABILITY_DIR": str(self.root)}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def record(self, event: dict[str, object]) -> None:
        subprocess.run(
            [sys.executable, RECORDER, json.dumps(event)], env=self.env, check=True
        )

    def events(self) -> list[dict[str, object]]:
        files = list((self.root / "events").glob("*.jsonl"))
        try:
            return [json.loads(line) for line in files[0].read_text().splitlines()]
        except (IndexError, OSError, json.JSONDecodeError) as exc:
            self.fail(f"failed to read event journal: {exc}")

    def test_event_journal_and_live_state(self) -> None:
        skill = self.root / "skills/tdd/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# TDD\n", encoding="utf-8")
        base = {"agent": "pi", "session_id": "s1", "cwd": "/tmp"}

        self.record({**base, "event": "session_started", "state": "idle"})
        self.record({**base, "event": "agent_started", "state": "working"})
        self.record(
            {
                **base,
                "event": "skill_activated",
                "skill": "tdd",
                "skill_path": str(skill),
            }
        )
        self.record({**base, "event": "agent_end", "state": "idle"})

        live_files = list((self.root / "live").glob("*.json"))
        try:
            live = json.loads(live_files[0].read_text())
        except (IndexError, OSError, json.JSONDecodeError) as exc:
            self.fail(f"failed to read live state: {exc}")
        self.assertEqual(live["state"], "idle")
        self.assertEqual(live["skills"], ["tdd"])
        activated = self.events()[2]
        self.assertTrue(str(activated["skill_version"]).startswith("sha256:"))
        self.assertEqual(activated["cwd"], "tmp")
        self.assertNotIn("skill_path", activated)

        self.record({**base, "event": "session_ended", "state": "idle"})
        self.assertEqual(list((self.root / "live").glob("*.json")), [])

    def test_codex_hook_translation_omits_prompt(self) -> None:
        skill = self.root / "skills/ponytail/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# Ponytail\n", encoding="utf-8")
        deployed_recorder = self.root / ".local/bin/agent-observability-record"
        deployed_recorder.parent.mkdir(parents=True)
        deployed_recorder.symlink_to(RECORDER)
        env = {**self.env, "HOME": str(self.root)}
        env.pop("AGENT_OBSERVABILITY_RECORDER", None)

        prompts = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "c1",
            "turn_id": "t1",
            "cwd": str(self.root),
            "model": "gpt-test",
            "prompt": "Use $ponytail on secret material",
        }
        reads = {
            **prompts,
            "hook_event_name": "PreToolUse",
            "tool_name": "read",
            "tool_input": {"path": str(skill)},
            "tool_use_id": "tool-1",
        }
        test_run = {
            **prompts,
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "python -m pytest"},
        }
        build_run = {
            **prompts,
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "nix build"},
        }
        diagnostic_warning = {
            **prompts,
            "hook_event_name": "PreToolUse",
            "tool_name": "lens_diagnostics",
            "tool_input": {"mode": "all"},
        }
        warning_result = {
            **diagnostic_warning,
            "hook_event_name": "PostToolUse",
            "tool_response": {"details": {"totalWarnings": 2}},
        }
        diagnostic_error = {**diagnostic_warning, "tool_use_id": "diagnostic-error"}
        error_result = {
            **diagnostic_error,
            "hook_event_name": "PostToolUse",
            "tool_response": {"details": {"totalErrors": 1}},
        }
        for hook in (
            prompts,
            reads,
            test_run,
            build_run,
            diagnostic_warning,
            warning_result,
            diagnostic_error,
            error_result,
        ):
            subprocess.run(
                [sys.executable, CODEX],
                input=json.dumps(hook),
                text=True,
                env=env,
                check=True,
            )

        events = self.events()
        self.assertEqual(
            [event["skill"] for event in events if event["event"] == "skill_activated"],
            ["ponytail", "ponytail"],
        )
        self.assertNotIn("secret material", json.dumps(events))
        self.assertTrue(all(event.get("schema_version") == 2 for event in events))
        self.assertEqual(
            [
                event["verification"]
                for event in events
                if event["event"] == "verification_started"
            ],
            ["test", "build", "diagnostics", "diagnostics"],
        )
        self.assertEqual(
            [
                event["status"]
                for event in events
                if event["event"] == "verification_finished"
            ],
            ["passed", "failed"],
        )
        self.assertEqual(
            [
                (event.get("diagnostics"), event.get("warnings"))
                for event in events
                if event["event"] == "verification_finished"
            ],
            [(0, 2), (1, 0)],
        )

    def test_ponytail_eval_fixture_and_dry_run(self) -> None:
        workspace = self.root / "eval-workspace"
        shutil.copytree(EVAL_FIXTURE, workspace)
        baseline = subprocess.run(
            [sys.executable, EVAL_VERIFIER, workspace], check=False
        )
        self.assertEqual(baseline.returncode, 1)

        pricing_path = workspace / "pricing.py"
        try:
            pricing = pricing_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.fail(f"failed to read fixture: {exc}")
        pricing_path.write_text(
            "from functools import cache\n\n"
            + pricing.replace("def get_rate", "@cache\ndef get_rate"),
            encoding="utf-8",
        )
        fixed = subprocess.run([sys.executable, EVAL_VERIFIER, workspace], check=False)
        self.assertEqual(fixed.returncode, 0)

        completed = subprocess.run(
            [sys.executable, EVALUATOR, EVAL_CASE, "--runs", "1", "--dry-run"],
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            plan = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"invalid eval plan: {exc}")
        self.assertIn("--skill", plan["treatment_command"])
        self.assertNotIn("--skill", plan["control_command"])
        self.assertIn(
            "This is an automated skill evaluation run. Do not create or modify eval cases.",
            plan["control_command"],
        )
        for case_name in ("tdd-inventory", "diagnosis-parser"):
            subprocess.run(
                [
                    sys.executable,
                    EVALUATOR,
                    REPO / f".agents/evals/{case_name}.json",
                    "--runs",
                    "1",
                    "--dry-run",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

    def test_eval_audit_classifies_without_deleting(self) -> None:
        result_dir = self.root / "eval-results"
        result_dir.mkdir()
        observed = [
            {"case": "ponytail-cache", "variant": "control", "success": False},
            {"case": "ponytail-cache", "variant": "treatment", "success": True},
            {"case": "ponytail-cache", "variant": "control", "success": False},
            {"case": "ponytail-cache", "variant": "treatment", "success": True},
            {"case": "ponytail-cache", "variant": "control", "success": False},
            {"case": "ponytail-cache", "variant": "treatment", "success": True},
        ]
        (result_dir / "results.jsonl").write_text(
            "".join(json.dumps(item) + "\n" for item in observed), encoding="utf-8"
        )
        cases_dir = REPO / ".agents/evals"
        before = sorted(cases_dir.glob("*.json"))
        completed = subprocess.run(
            [
                sys.executable,
                AUDITOR,
                "--cases",
                cases_dir,
                "--results",
                self.root,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        report = {item["case"]: item for item in json.loads(completed.stdout)}
        self.assertEqual(report["ponytail-cache"]["status"], "keep")
        self.assertEqual(report["tdd-inventory"]["status"], "review")
        self.assertEqual(before, sorted(cases_dir.glob("*.json")))

    def test_report_deduplicates_skill_and_attributes_verification(self) -> None:
        base = {
            "agent": "pi",
            "session_id": "report-session",
            "cwd": "/private/work/super-secret-project",
            "model": "test-model",
        }
        self.record({**base, "event": "agent_started", "state": "working"})
        self.record(
            {
                **base,
                "event": "skill_activated",
                "skill": "tdd",
                "invocation": "explicit",
            }
        )
        self.record(
            {**base, "event": "skill_activated", "skill": "tdd", "invocation": "read"}
        )
        self.record(
            {
                **base,
                "event": "verification_started",
                "verification": "test",
                "tool": "bash",
            }
        )
        self.record(
            {
                **base,
                "event": "verification_finished",
                "verification": "test",
                "status": "passed",
            }
        )
        self.record({**base, "event": "agent_end", "state": "idle"})

        eval_dir = self.root / "eval-results"
        eval_dir.mkdir()
        timestamp = self.events()[0]["ts"]
        eval_results = [
            {
                "ts": timestamp,
                "case": "tdd-inventory",
                "skill": "tdd",
                "agent": "pi",
                "model": "test-model",
                "variant": "control",
                "success": False,
                "changed_lines": 10,
                "failure_kind": "verifier_failed",
                "failure_phase": "verifier",
                "expected_behavior": "expected behavior",
                "failure_conditions": ["bad result"],
            },
            {
                "ts": timestamp,
                "case": "tdd-inventory",
                "skill": "tdd",
                "agent": "pi",
                "model": "test-model",
                "variant": "treatment",
                "success": True,
                "changed_lines": 2,
            },
        ]
        (eval_dir / "results.jsonl").write_text(
            "".join(json.dumps(result) + "\n" for result in eval_results),
            encoding="utf-8",
        )

        subprocess.run(
            [sys.executable, REPORTER, "--days", "1"],
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            report = (self.root / "report.html").read_text(encoding="utf-8")
            eval_report = (self.root / "evals.html").read_text(encoding="utf-8")
        except OSError as exc:
            self.fail(f"failed to read report: {exc}")
        self.assertIn("Skillを含むturn", report)
        self.assertIn("super-secret-project", report)
        self.assertNotIn("/private/work", report)
        self.assertIn("bash 1", report)
        self.assertIn('<tr class="data-row search-row"><td data-label="時刻">', report)
        self.assertIn('href="evals.html"', report)
        self.assertNotIn("Skillあり／なし比較", report)
        self.assertIn('id="tdd-inventory"', eval_report)
        self.assertIn('class=data-row data-eval-skill="tdd"', eval_report)
        self.assertIn("filter(row => row.cells.length > index)", eval_report)
        self.assertIn("+100pt", eval_report)
        self.assertIn("暫定", eval_report)
        self.assertIn("0 → 2", eval_report)
        self.assertIn("verifier_failed", eval_report)
        self.assertIn("条件を見る", eval_report)
        self.assertIn("同じfixture・課題・verifierでskillを読み込まない", eval_report)
        self.assertIn("Inventory.reserve behavior", eval_report)
        self.assertIn("失敗詳細", eval_report)
        self.assertIn("期待: expected behavior", eval_report)
        self.assertIn("条件: bad result", eval_report)

    def test_report_uses_latest_result_per_verification_category(self) -> None:
        base = {
            "agent": "pi",
            "session_id": "verification-session",
            "cwd": "/tmp/project",
        }
        self.record({**base, "event": "agent_started", "state": "working"})
        self.record({**base, "event": "skill_activated", "skill": "tdd"})
        for verification, status in (
            ("test", "failed"),
            ("test", "passed"),
            ("diagnostics", "failed"),
        ):
            self.record(
                {
                    **base,
                    "event": "verification_finished",
                    "verification": verification,
                    "status": status,
                    **({"diagnostics": 3} if verification == "diagnostics" else {}),
                }
            )
        self.record({**base, "event": "agent_end", "state": "idle"})
        legacy = {**base, "session_id": "legacy-session", "schema_version": 1}
        self.record({**legacy, "event": "agent_started", "state": "working"})
        self.record({**legacy, "event": "skill_activated", "skill": "tdd"})
        self.record({**legacy, "event": "agent_end", "state": "idle"})

        subprocess.run(
            [sys.executable, REPORTER, "--days", "1"],
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )
        report = (self.root / "report.html").read_text(encoding="utf-8")
        self.assertIn('<td data-label="失敗" class=bad>1</td>', report)
        self.assertIn('<td data-label="検証済" class=good>0</td>', report)
        self.assertIn(
            '<td data-label="結果">検証失敗<small>diagnostics: 失敗（error 3件） / test: 成功</small>',
            report,
        )
        self.assertIn("旧形式 1", report)
        self.assertIn('<td data-label="結果">旧形式', report)


if __name__ == "__main__":
    unittest.main()
