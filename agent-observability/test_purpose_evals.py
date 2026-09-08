from __future__ import annotations
import importlib.util
import json
import os
import pathlib
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from eval_contracts import case_verdict, contract_version, load_catalog, reviewed_result

REPO = pathlib.Path(__file__).resolve().parents[1]
CASES = REPO / ".agents/evals"
spec = importlib.util.spec_from_file_location(
    "evaluator", REPO / "agent-observability/evaluate-skill.py"
)
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


class MemoryWorker:
    """Unit-test worker; production never selects this implementation."""

    def __init__(self, docker):
        self.docker = docker
        self.name = "unit-worker"

    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        return self

    def __exit__(self, *_):
        self.temp.cleanup()

    def load_fixture(self, root):
        for name, data in evaluator.snapshot(root).items():
            self.write(name, data)

    def load_skill(self, root):
        pass

    def load_readonly(self, files):
        pass

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def snapshot(self):
        return evaluator.snapshot(self.root)

    def bash(self, command, timeout):
        result = subprocess.run(shlex.split(command), cwd=self.root, timeout=timeout)
        return subprocess.CompletedProcess(
            result.args,
            result.returncode,
            result.stdout.encode(),
            result.stderr.encode(),
        )


class PurposeEvalTest(unittest.TestCase):
    def setUp(self):
        worker_patch = patch.object(evaluator, "ToolSandbox", MemoryWorker)
        worker_patch.start()
        self.addCleanup(worker_patch.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.case = json.loads((CASES / "purpose-test-design-clean.json").read_text())

    def tearDown(self):
        self.temp.cleanup()

    def records(self, control=False, treatment=True):
        return [
            dict(
                experiment_id="experiment",
                contract_version="version",
                model="test/model",
                agent="pi",
                agent_version="1",
                run=i,
                variant=v,
                success=success,
                ts="2026-01-01",
                failure_kind="passed",
            )
            for i in range(1, 4)
            for v, success in [("control", control), ("treatment", treatment)]
        ]

    def test_legacy_evidence_never_decides_skill_adoption(self):
        self.assertEqual(
            case_verdict({"evaluation": {"status": "legacy"}}, self.records())[0],
            "hold",
        )

    def test_no_difference_or_both_fail_does_not_retire(self):
        for both in (True, False):
            self.assertEqual(
                case_verdict(self.case, self.records(both, both))[0],
                "neutral" if both else "hold",
            )

    def test_paired_improvement_and_regression(self):
        self.assertEqual(case_verdict(self.case, self.records())[0], "keep")
        self.assertEqual(
            case_verdict(self.case, self.records(True, False))[0], "revise"
        )

    def test_incomplete_duplicate_mixed_stale_and_ungraded_are_held(self):
        for mutate in (
            "incomplete",
            "duplicate",
            "mixed",
            "ungraded",
            "environment",
            "stale",
        ):
            rows = self.records()
            if mutate == "incomplete":
                rows.pop()
            if mutate == "duplicate":
                rows.append(dict(rows[-1]))
            if mutate == "mixed":
                rows[0]["model"] = "other"
            if mutate == "ungraded":
                rows[0]["success"] = None
            if mutate == "environment":
                rows[0]["failure_kind"] = "timeout"
            version = "new" if mutate == "stale" else "version"
            with self.subTest(mutate=mutate):
                self.assertEqual(
                    case_verdict(self.case, rows, current_version=version)[0], "hold"
                )

    def test_fingerprint_tracks_supporting_files_and_fixture(self):
        fixture = self.root / "fixture"
        fixture.mkdir()
        (fixture / "input").write_text("first")
        skill = self.root / "skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("main")
        (skill / "reference.md").write_text("one")
        case = {
            "fixture": "fixture",
            "skill_path": "skill/SKILL.md",
            "verifiers": [["true"]],
        }
        path = self.root / "case.json"
        before = contract_version(case, path)
        (skill / "reference.md").write_text("two")
        after = contract_version(case, path)
        self.assertNotEqual(before, after)
        (fixture / "input").write_text("second")
        self.assertNotEqual(after, contract_version(case, path))

    def test_explicit_skill_and_no_global_context(self):
        command = evaluator.pi_command(
            "task",
            CASES.parent / "installed-skills/engineering/tdd/SKILL.md",
            "test/model",
        )
        self.assertIn("--no-context-files", command)
        self.assertIn("--no-extensions", command)
        self.assertIn("--no-builtin-tools", command)
        self.assertIn("--extension", command)
        self.assertNotIn("--tools", command)
        self.assertTrue(any("TDD is the red" in token for token in command))
        self.assertFalse(any("system-append.md" in token for token in command))

    def test_outcome_no_change_and_verifier_mutations_not_agent_changes(self):
        case = dict(self.case, rubric=[])
        invocations = []

        def run(cmd, **kwargs):
            invocations.append(cmd)
            if cmd[0] != "pi":
                (pathlib.Path(kwargs["cwd"]) / "verifier-noise.txt").write_text(
                    "not agent work"
                )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with (
            patch.object(evaluator, "ROOT", self.root),
            patch.object(evaluator.subprocess, "run", side_effect=run),
        ):
            result = evaluator.run_once(
                case,
                CASES / "purpose-test-design-clean.json",
                "control",
                1,
                "test/model",
                30,
                "test",
            )
        self.assertTrue(result["success"])
        self.assertEqual(result["changed_files"], 0)
        self.assertFalse(
            (pathlib.Path(result["artifacts"]) / "after/verifier-noise.txt").exists()
        )

    def test_review_needs_all_criteria_evidence_and_unchanged_artifacts(self):
        with patch.object(evaluator, "ROOT", self.root):
            directory, version = evaluator.persist_artifacts(
                self.case,
                {},
                {
                    "findings.md": b"No issue.",
                    "__pycache__/synthetic.pyc": b"synthetic cached bytecode",
                },
                "trace",
                "",
                "exp",
                1,
                "control",
            )
        item = {
            "rubric": self.case["rubric"],
            "failure_kind": "passed",
            "success": None,
            "artifacts": directory,
            "artifact_version": version,
        }
        self.assertIsNone(reviewed_result(item)["success"])
        path = pathlib.Path(directory) / "review.json"
        review = json.loads(path.read_text())
        review["reviewer"] = "test reviewer"
        for row in review["criteria"]:
            row.update({"pass": True, "evidence": "findings.md:1"})
        path.write_text(json.dumps(review))
        self.assertTrue(reviewed_result(item)["success"])
        review["criteria"][0]["evidence"] = ""
        path.write_text(json.dumps(review))
        self.assertIsNone(reviewed_result(item)["success"])
        review["criteria"][0]["evidence"] = "findings.md:1"
        path.write_text(json.dumps(review))
        (path.parent / "after/findings.md").write_text("changed")
        self.assertIsNone(reviewed_result(item)["success"])

    def test_failed_execution_cannot_be_overridden_by_review(self):
        self.assertFalse(
            reviewed_result(
                {"rubric": [{"id": "a"}], "failure_kind": "timeout", "success": False}
            )["success"]
        )

    def test_agent_and_verifier_timeout_are_recorded(self):
        for error in ("agent", "verifier"):

            def run(cmd, **kwargs):
                if (cmd[0] == "pi") == (error == "agent"):
                    raise subprocess.TimeoutExpired(cmd, 1)
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            with (
                patch.object(evaluator, "ROOT", self.root / error),
                patch.object(evaluator.subprocess, "run", side_effect=run),
            ):
                result = evaluator.run_once(
                    self.case,
                    CASES / "purpose-test-design-clean.json",
                    "control",
                    1,
                    "test/model",
                    1,
                    "exp",
                )
            self.assertEqual(
                result["failure_kind"],
                "timeout" if error == "agent" else "verifier_error",
            )

    def test_inventory_catalog_is_complete_and_legacy_reasons_present(self):
        names = {
            p.parent.name
            for prefix in ("skills", "installed-skills")
            for p in (CASES.parent / prefix).glob("**/SKILL.md")
        }
        self.assertEqual(names, set(load_catalog()))
        cases = [json.loads(p.read_text()) for p in CASES.glob("*.json")]
        # Classification is declared by the contract, not by a filename prefix.
        for case in cases:
            self.assertIn(case["evaluation"]["status"], ("legacy", "ready"))
        legacy = [c for c in cases if c["evaluation"]["status"] == "legacy"]
        self.assertTrue(legacy)
        self.assertTrue(all(c["evaluation"]["reason"].strip() for c in legacy))

    def verify(self, id, prepare=None):
        case = json.loads((CASES / (id + ".json")).read_text())
        workspace = self.root / id
        shutil.copytree(CASES / case["fixture"], workspace)
        if prepare:
            prepare(workspace)
        cmd = evaluator.verifier_commands(case, CASES / (id + ".json"), workspace)[0]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPYCACHEPREFIX": str(self.root / "pycache")},
        ).returncode

    def test_review_gate_accepts_paraphrase_and_detects_input_tampering(self):
        self.assertEqual(self.verify("purpose-test-design-clean"), 1)
        shutil.rmtree(self.root / "purpose-test-design-clean")
        self.assertEqual(
            self.verify(
                "purpose-test-design-clean",
                lambda p: (p / "findings.md").write_text(
                    "入力値が期待値の隣にあり、修正不要。"
                ),
            ),
            0,
        )
        shutil.rmtree(self.root / "purpose-test-design-clean")

        def tamper(p):
            (p / "findings.md").write_text("fine")
            (p / "pricing.py").write_text("changed")

        self.assertEqual(self.verify("purpose-test-design-clean", tamper), 1)

    def test_cache_gate_rejects_original_and_accepts_two_equivalent_fixes(self):
        id = "purpose-ponytail-minimal-cache"
        self.assertEqual(self.verify(id), 1)
        for solution in ("from functools import cache\n\n", ""):
            shutil.rmtree(self.root / id)

            def fix(p):
                path = p / "pricing.py"
                text = path.read_text()
                if solution:
                    text = solution + text.replace(
                        "def get_rate", "@cache\ndef get_rate"
                    )
                else:
                    text = text.replace(
                        "def get_rate(currency: str) -> float:\n    return fetch_rate(currency)",
                        "_cache = {}\n\ndef get_rate(currency: str) -> float:\n    if currency not in _cache:\n        _cache[currency] = fetch_rate(currency)\n    return _cache[currency]",
                    )
                path.write_text(text)

            self.assertEqual(self.verify(id, fix), 0)

    def test_tdd_gate_checks_invalid_quantities_and_mutation_detection(self):
        id = "purpose-tdd-red-green"
        self.assertEqual(self.verify(id), 1)
        shutil.rmtree(self.root / id)

        def fix(p):
            (p / "inventory.py").write_text(
                "class Inventory:\n    def __init__(self, stock): self.stock=stock\n    def reserve(self, quantity):\n        if quantity<=0 or quantity>self.stock: raise ValueError()\n        self.stock-=quantity\n        return self.stock\n"
            )
            (p / "test_regression.py").write_text(
                "import unittest\nfrom inventory import Inventory\nclass Regression(unittest.TestCase):\n    def test_rejected_reservation_preserves_stock(self):\n        inv=Inventory(10)\n        with self.assertRaises(ValueError): inv.reserve(11)\n        self.assertEqual(inv.stock,10)\n"
            )

        self.assertEqual(self.verify(id, fix), 0)

    def test_all_purpose_cases_have_failing_empty_output_gate(self):
        for path in sorted(CASES.glob("purpose-*.json")):
            with self.subTest(case=path.stem):
                self.assertEqual(self.verify(path.stem), 1)

    def test_parser_preserves_signed_and_whitespace_inputs(self):
        def fix(p):
            (p / "parser.py").write_text(
                "def parse_count(value):\n    return int(value.strip())\n"
            )
            (p / "diagnosis.md").write_text(
                "ValueError was converted to zero. Removed that fallback."
            )
            (p / "test_regression.py").write_text(
                "import unittest\nfrom parser import parse_count\nclass Regression(unittest.TestCase):\n    def test_malformed_raises(self):\n        with self.assertRaises(ValueError): parse_count('bad')\n"
            )

        self.assertEqual(self.verify("purpose-diagnosis-feedback", fix), 0)

    def test_ready_case_requires_purpose_rubric(self):
        broken = dict(self.case, rubric=[])
        path = self.root / "case.json"
        path.write_text(json.dumps(broken))
        with self.assertRaises(ValueError):
            evaluator.load_case(path)

    def test_cli_pause_prevents_model_or_auth_execution(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        marker = self.root / "pi-was-called"
        fake = bin_dir / "pi"
        fake.write_text("#!/bin/sh\ntouch " + str(marker) + "\nexit 99\n")
        fake.chmod(0o755)
        env = {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]}
        command = [
            sys.executable,
            str(REPO / "agent-observability/evaluate-skill.py"),
            str(CASES / "purpose-test-design-clean.json"),
            "--runs",
            "1",
            "--model",
            "synthetic/test",
        ]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("実評価は停止中", result.stderr)
        self.assertFalse(marker.exists())
        dry_run = subprocess.run(
            command + ["--dry-run"], env=env, capture_output=True, text=True
        )
        self.assertEqual(dry_run.returncode, 0)
        self.assertFalse(marker.exists())

    def test_monitor_is_quiet_without_changes(self):
        cmd = [
            sys.executable,
            str(REPO / "agent-observability/audit-evals.py"),
            "--changes",
            "--results",
            str(self.root),
        ]
        first = json.loads(subprocess.check_output(cmd))
        second = json.loads(subprocess.check_output(cmd))
        self.assertTrue(first["initial_snapshot"])
        self.assertEqual(second["changes"], [])

    def test_dry_run_pairs_stay_adjacent_and_include_candidate(self):
        result = subprocess.check_output(
            [
                sys.executable,
                str(REPO / "agent-observability/evaluate-skill.py"),
                str(CASES / "purpose-tdd-red-green.json"),
                "--runs",
                "3",
                "--dry-run",
                "--candidate",
                str(CASES.parent / "installed-skills/engineering/tdd/SKILL.md"),
            ]
        )
        plan = json.loads(result)
        for i in range(3):
            pair = plan["runs"][i * 3 : i * 3 + 3]
            self.assertEqual({row[0] for row in pair}, {i + 1})
            self.assertEqual(
                {row[1] for row in pair}, {"control", "treatment", "candidate"}
            )


if __name__ == "__main__":
    unittest.main()
