import importlib.util
from pathlib import Path
import sys
import json
from unittest.mock import patch
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('operations_report', Path(__file__).with_name('generate-report.py'))
report = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = report
spec.loader.exec_module(report)

class OperationsDashboardTest(unittest.TestCase):
    def test_empty_and_corrupt_round_are_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIn('評価ラウンドはありません', report.render_operations(30, root))
            folder = root / 'eval-loops' / 'broken'
            folder.mkdir(parents=True)
            (folder / 'plan.json').write_text('{')
            (folder / 'decision.json').write_text('{"action":"adopt","reason":"<script>alert(1)</script>"}')
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            output = report.render_operations(30, root)
            self.assertIn('対象不明・破損・別形式の検証を含みます', output)
            self.assertIn('未確定の記録', output)
            self.assertNotIn('<script>alert(1)</script>', output)
            self.assertIn('usage.html', output)
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_retired_round_is_hidden_but_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'eval-loops' / 'retired-example'
            folder.mkdir(parents=True)
            plan = folder / 'plan.json'
            plan.write_text('{"skill":"removed-synthetic-skill"}')
            output = report.render_operations(30, root)
            self.assertNotIn('retired-example', output)
            self.assertNotIn('removed-synthetic-skill', output)
            self.assertNotIn('除外した履歴', output)
            self.assertTrue(plan.exists())


class EvaluationEvidenceDisplayTest(unittest.TestCase):
    def rows(self, control_success, treatment_success, version="current"):
        return [
            {"skill": "sample", "case": "sample-case", "experiment_id": "experiment",
             "contract_version": version, "model": "sample-model", "agent": "sample-agent",
             "agent_version": "1", "skill_version": "skill-v1", "ts": "2026-01-01",
             "run": run, "variant": variant, "success": success, "failure_kind": "passed"}
            for run in range(1, 4)
            for variant, success in (("control", control_success), ("treatment", treatment_success))
        ]

    def render_rows(self, rows):
        with patch.object(report, "contract_version", return_value="current"):
            return report.render_eval_rows(rows, {}, {"sample-case": {"evaluation": {"status": "ready"}}}, include_contract=False)

    def test_ungraded_or_absent_side_is_not_a_measured_quality_difference(self):
        rows = self.rows(False, True)
        self.assertIn("+100pt", self.render_rows(rows))
        self.assertIn("継続候補", self.render_rows(rows))
        for incomplete in (self.rows(None, True), [r for r in rows if r["variant"] == "treatment"]):
            with self.subTest(rows=incomplete):
                output = self.render_rows(incomplete)
                self.assertNotIn("+100pt", output)
                self.assertIn("未採点・片側欠落", output)
        self.assertIn("未採点 3", self.render_rows(self.rows(None, True)))

    def test_stale_winning_results_are_not_a_current_continuation_candidate(self):
        output = self.render_rows(self.rows(False, True, version="previous"))
        self.assertNotIn("継続候補", output)
        self.assertIn("評価対象が更新済み", output)

    def test_supplementary_screen_links_keep_limitations_without_creating_a_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "eval-loops" / "sample-screen"
            folder.mkdir(parents=True)
            (folder / "report.md").write_text("# Synthetic screen")
            (folder / "report.json").write_text(json.dumps({
                "plan": {"runtime": "sample-cli", "model": "sample-model", "mode": "screen", "runs": 1},
                "conclusion": {"reason": "<script>passed</script>", "limitations": ["One run; no holdout"]}
            }))
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            output = report.render_saved_reports(root)
            self.assertIn((folder / "report.md").resolve().as_uri(), output)
            self.assertIn("One run; no holdout", output)
            self.assertIn("各条件1回", output)
            self.assertNotIn("<script>passed</script>", output)
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})
            (folder / "report.json").write_text("{")
            self.assertIn((folder / "report.md").resolve().as_uri(), report.render_saved_reports(root))


class CrossPageEvidenceTest(unittest.TestCase):
    def test_reference_execution_is_visible_on_inventory_and_cases_without_adoption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "sample" / "SKILL.md"
            skill.parent.mkdir()
            skill.write_text("# Sample")
            folder = root / "eval-loops" / "sample-screen"
            folder.mkdir(parents=True)
            (folder / "report.md").write_text("# One screening run; no adoption")
            (folder / "report.json").write_text(json.dumps({
                "plan": {"runtime": "sample-cli", "model": "sample-model", "mode": "screen"},
                "results": [{"case": "sample-case", "exit_code": 0, "timed_out": False,
                             "exact_final_files": True, "no_unexpected_changes": True,
                             "verification_required": False}]
            }))
            catalog = {"sample": {"path": str(skill), "source": "authored", "purpose": "Sample",
                       "evidence": "Exact edit", "required_scenarios": ["typical"],
                       "decision": "unassessed", "decision_reason": "No adoption", "script_candidate": "None"}}
            cases = {"sample-case": {"id": "sample-case", "skill": "sample", "evaluation": {"status": "ready"}}}
            with patch.object(report, "ROOT", root), patch.object(report, "load_catalog", return_value=catalog), patch.object(report, "load_eval_cases", return_value=cases), patch.object(report, "load_eval_results", return_value=[]), patch.object(report, "load_skill_locations", return_value={}):
                inventory = report.render_operations(30, root)
                evaluations = report.render_evaluations(30, [])
            for page in (inventory, evaluations):
                self.assertIn("実行記録あり 1 / 1ケース", page)
            self.assertIn("参考検証 1/1成功", evaluations)
            self.assertIn("実行履歴（1件）", evaluations)
            self.assertNotIn("保存済みアウトプットなし", evaluations)
            self.assertNotIn("表示期間内に比較評価の結果がありません", evaluations)
            self.assertIn("判断材料不足", inventory)
            self.assertNotIn("修正版の採用判断あり", inventory)

            evidence = report.EvidenceSnapshot(root, cases, [], catalog, {})
            pages = {"report.html": inventory, "evals.html": evaluations,
                     "usage.html": report.render_overview(30, [], {})}
            report.validate_pages(pages, evidence)
            mutations = [
                ("report.html", "実行記録あり 1 / 1ケース", "実行記録あり 0 / 1ケース"),
                ("evals.html", 'data-evidence="recorded"', 'data-evidence="missing"'),
                ("evals.html", 'data-history-case="sample-case"', 'data-history-case="wrong-case"'),
                ("evals.html", 'data-metric="recorded-cases">1', 'data-metric="recorded-cases">0'),
                ("evals.html", 'report.html#skill-status', 'report.html#missing-anchor'),
                ("usage.html", '<style>', '<style>/* stale style */'),
                ("usage.html", 'data-metric="usage-total">0', 'data-metric="usage-total">1'),
            ]
            for name, old, new in mutations:
                with self.subTest(corruption=old), self.assertRaises(ValueError):
                    report.validate_pages({**pages, name: pages[name].replace(old, new)}, evidence)


class MissingEvidenceDisplayTest(unittest.TestCase):
    def test_ungraded_is_not_reported_as_a_failure(self):
        output = report.render_eval_details([{"success": None, "variant": "control", "failure_kind": "passed"}])
        self.assertIn("1件の未採点", output)
        self.assertNotIn("1件の失敗", output)
        self.assertIn("未記録", report.render_eval_details([{"success": False}]))

    def test_missing_metrics_are_not_zero_measurements(self):
        output = report.render_eval_rows([{"skill": "sample", "case": "sample", "variant": "treatment", "success": True}], {}, {}, include_contract=False)
        self.assertIn("— → —", output)
        self.assertNotIn("0 → 0", output)

    def test_artifact_links_follow_actual_file_availability(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp).resolve()
            items = [{"artifacts": str(folder), "variant": "control", "success": None}]
            output = report.render_artifacts(items)
            self.assertNotIn('href="' + (folder / "index.html").as_uri(), output)
            self.assertIn("未保存・参照先なし", output)
            (folder / "index.html").write_text("<p>Output</p>")
            self.assertIn('href="' + (folder / "index.html").as_uri(), report.render_artifacts(items))
            self.assertNotIn('href="' + (folder / "review.json").as_uri(), report.render_artifacts(items))
            for path in ("relative/output", ["invalid-path"]):
                self.assertIn("保存先のパスを確認できません", report.render_artifacts([dict(items[0], artifacts=path)]))

    def test_usage_total_includes_legacy_and_missing_end_records(self):
        stats = {"sample": report.SkillStats(uses=3, verified=1, ongoing=1, legacy=1)}
        output = report.render_overview(30, [], stats)
        self.assertIn('data-metric="usage-no-end">1', output)
        self.assertIn('data-metric="usage-legacy">1', output)
        self.assertIn('data-label="終了記録なし">1', output)
