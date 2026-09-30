#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
REPORTER = REPO / "agent-observability/generate-report.py"
EVALUATOR = REPO / "agent-observability/evaluate-skill.py"
AUDITOR = REPO / "agent-observability/audit-evals.py"
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

    def write_event(self, event: dict[str, object]) -> None:
        """Write a saved-event fixture without invoking the retired collector."""
        directory = self.root / "events"
        directory.mkdir(exist_ok=True)
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "schema_version": 2,
            **event,
        }
        with (directory / "sample.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")

    def events(self) -> list[dict[str, object]]:
        return [
            json.loads(line)
            for line in (self.root / "events/sample.jsonl").read_text().splitlines()
        ]

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
        self.assertIn("--no-builtin-tools", plan["treatment_command"])
        self.assertTrue(
            any("Apply this skill" in part for part in plan["treatment_command"])
        )
        self.assertNotIn("--skill", plan["control_command"])
        self.assertIn(
            "This is an automated skill evaluation run. Do not create or modify eval cases.",
            " ".join(plan["control_command"]),
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
        self.assertEqual(report["ponytail-cache"]["status"], "hold")
        self.assertEqual(report["tdd-inventory"]["status"], "hold")
        self.assertEqual(before, sorted(cases_dir.glob("*.json")))

    def test_report_deduplicates_skill_and_attributes_verification(self) -> None:
        base = {
            "agent": "pi",
            "session_id": "report-session",
            "cwd": "/private/work/super-secret-project",
            "model": "test-model",
        }
        self.write_event({**base, "event": "agent_started", "state": "working"})
        self.write_event(
            {
                **base,
                "event": "skill_activated",
                "skill": "tdd",
                "invocation": "explicit",
            }
        )
        self.write_event(
            {**base, "event": "skill_activated", "skill": "tdd", "invocation": "read"}
        )
        self.write_event(
            {
                **base,
                "event": "verification_started",
                "verification": "test",
                "tool": "bash",
            }
        )
        self.write_event(
            {
                **base,
                "event": "verification_finished",
                "verification": "test",
                "status": "passed",
            }
        )
        self.write_event({**base, "event": "agent_end", "state": "idle"})

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
            report = (self.root / "usage.html").read_text(encoding="utf-8")
            eval_report = (self.root / "evals.html").read_text(encoding="utf-8")
        except OSError as exc:
            self.fail(f"failed to read report: {exc}")
        self.assertIn("スキル別の利用と作業検証", report)
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
        self.assertIn("判断保留", eval_report)
        self.assertIn("— → 2", eval_report)
        self.assertIn("verifier_failed", eval_report)
        self.assertIn("条件を見る", eval_report)
        self.assertIn("同じテストデータ・課題・検証プログラムを使い、対象スキルを読み込まない", eval_report)
        self.assertIn("Inventory.reserve behavior", eval_report)
        self.assertIn("失敗詳細", eval_report)
        self.assertIn("期待: expected behavior", eval_report)
        self.assertIn("条件: bad result", eval_report)

    def test_report_works_when_invoked_through_symlink(self) -> None:
        deployed_reporter = self.root / ".local/bin/agent-observability-report"
        deployed_reporter.parent.mkdir(parents=True)
        deployed_reporter.symlink_to(REPORTER)

        result = subprocess.run(
            [deployed_reporter, "--days", "1"],
            env=self.env,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "report.html").is_file())

    def test_report_uses_latest_result_per_verification_category(self) -> None:
        base = {
            "agent": "pi",
            "session_id": "verification-session",
            "cwd": "/tmp/project",
        }
        self.write_event({**base, "event": "agent_started", "state": "working"})
        self.write_event({**base, "event": "skill_activated", "skill": "tdd"})
        for verification, status in (
            ("test", "failed"),
            ("test", "passed"),
            ("diagnostics", "failed"),
        ):
            self.write_event(
                {
                    **base,
                    "event": "verification_finished",
                    "verification": verification,
                    "status": status,
                    **({"diagnostics": 3} if verification == "diagnostics" else {}),
                }
            )
        self.write_event({**base, "event": "agent_end", "state": "idle"})
        legacy = {**base, "session_id": "legacy-session", "schema_version": 1}
        self.write_event({**legacy, "event": "agent_started", "state": "working"})
        self.write_event({**legacy, "event": "skill_activated", "skill": "tdd"})
        self.write_event({**legacy, "event": "agent_end", "state": "idle"})

        subprocess.run(
            [sys.executable, REPORTER, "--days", "1"],
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )
        report = (self.root / "usage.html").read_text(encoding="utf-8")
        self.assertIn('<td data-label="失敗" class=bad>1</td>', report)
        self.assertIn('<td data-label="検証済" class=good>0</td>', report)
        self.assertIn(
            '<td data-label="結果">検証失敗<small>diagnostics: 失敗（error 3件） / test: 成功</small>',
            report,
        )
        self.assertIn("旧形式 1", report)
        self.assertIn('<td data-label="結果">旧形式', report)

    def test_report_keeps_unconfirmed_verification_out_of_success_and_failure(self) -> None:
        base = {"agent": "codex", "session_id": "pending-result", "turn_id": "turn"}
        self.write_event({**base, "event": "agent_started"})
        self.write_event({**base, "event": "skill_activated", "skill": "tdd"})
        self.write_event({**base, "event": "verification_finished", "verification": "test", "status": "unknown"})
        self.write_event({**base, "event": "agent_end"})
        subprocess.run([sys.executable, REPORTER, "--days", "1"],
                       env=self.env, check=True, capture_output=True, text=True)
        report = (self.root / "usage.html").read_text(encoding="utf-8")
        self.assertIn('<td data-label="失敗" class=bad>0</td>', report)
        self.assertIn('<td data-label="検証済" class=good>0</td>', report)
        self.assertIn('<td data-label="結果">未検証<small>test: 未確認</small>', report)


if __name__ == "__main__":
    unittest.main()
