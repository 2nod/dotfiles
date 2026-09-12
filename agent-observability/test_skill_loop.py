"""Workflow gates use synthetic results; no model calls or live skill changes."""

import copy
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "skill_loop", pathlib.Path(__file__).with_name("skill-loop.py")
)
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)


class LoopTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(loop, "execution_preflight")
        guard.start()
        self.addCleanup(guard.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.case = {
            "id": "test",
            "skill": "demo",
            "scenario": "typical",
            "evaluation": {"status": "ready"},
            "rubric": [{"id": "quality"}],
        }
        self.case_path = self.root / "case.json"
        self.case_path.write_text(json.dumps(self.case))
        self.plan = {
            "skill": "demo",
            "purpose": "Useful outcome",
            "model": "fixed",
            "scope": "Offline scenario",
            "reviewer": "AI, not blind",
            "mode": "screen",
            "runs": 1,
            "max_calls": 2,
            "cases": [
                {
                    "path": str(self.case_path),
                    "contract_version": "version",
                    "alignment": "Tests goal",
                    "verifier_evidence": "baseline fails, two correct alternatives pass",
                }
            ],
            "candidate": None,
        }
        self.version = patch.object(loop, "contract_version", return_value="version")
        self.version.start()
        self.addCleanup(self.version.stop)

    def results(self, variants=("control", "treatment")):
        return [
            {
                "case": "test",
                "run": 1,
                "variant": v,
                "model": "fixed",
                "agent": "pi",
                "agent_version": "1",
                "contract_version": "version",
                "experiment_id": "experiment",
                "success": True,
                "failure_kind": "passed",
                "rubric": self.case["rubric"],
            }
            for v in variants
        ]

    def reviewed(self, items, action="hold"):
        (self.root / "started.json").write_text(json.dumps(self.plan))
        (self.root / "test.jsonl").write_text("\n".join(json.dumps(i) for i in items))
        (self.root / "decision.json").write_text(
            json.dumps(
                {
                    "action": action,
                    "reason": "reason",
                    "reviewer": "AI",
                    "evidence": "trace",
                    "limitations": "synthetic",
                    "next_check": "new scenarios",
                }
            )
        )
        return dict(self.plan, _directory=str(self.root))

    def test_status_tracks_evidence_without_launching(self):
        (self.root / "plan.json").write_text(json.dumps(self.plan))
        with patch.object(loop.subprocess, "run") as run:
            self.assertEqual(loop.status(self.root)["state"], "ready")
            (self.root / "started.json").write_text(json.dumps(self.plan))
            self.assertEqual(loop.status(self.root)["state"], "execution-incomplete")
            (self.root / "completed.json").write_text("{}")
            self.assertEqual(loop.status(self.root)["state"], "needs-review")
            with patch.object(loop, "reviewed_result", side_effect=lambda x: x):
                self.reviewed(self.results())
                (self.root / "decision.json").unlink()
                self.assertEqual(loop.status(self.root)["state"], "needs-decision")
                self.reviewed(self.results())
                self.assertEqual(loop.status(self.root)["state"], "decided")
            run.assert_not_called()

    def test_next_keeps_history_but_requires_new_plan_review(self):
        fixture = self.root / "fixture"
        fixture.mkdir()
        (fixture / "input.txt").write_text("unchanged input")
        self.case["fixture"] = "fixture"
        self.case_path.write_text(json.dumps(self.case))
        (self.root / "plan.json").write_text(json.dumps(self.plan))
        self.reviewed(self.results())
        (self.root / "completed.json").write_text("{}")
        destination = self.root / "next"
        with patch.object(loop, "reviewed_result", side_effect=lambda x: x), patch.object(loop, "load_catalog", return_value={"demo": {"source": "authored"}}):
            result = loop.next_round(self.root, destination)
            self.assertEqual(result["state"], "needs-plan")
            self.assertFalse((destination / "started.json").exists())
            self.assertFalse((destination / "test.jsonl").exists())
            plan = loop.read(destination / "plan.json")
            self.assertEqual(plan["lineage"]["parent"], str(self.root))
            plan["scope"] = "new comparison"
            plan["cases"][0]["holdout"] = True
            self.assertTrue(any("holdout" in e for e in loop.validate(plan)))
            with self.assertRaises(FileExistsError):
                loop.next_round(self.root, destination)

    def test_next_rejects_incomplete_and_installed_candidate(self):
        (self.root / "plan.json").write_text(json.dumps(self.plan))
        with self.assertRaises(ValueError):
            loop.next_round(self.root, self.root / "next")
        with patch.object(loop, "status", return_value={"state": "decided"}), patch.object(loop, "load_catalog", return_value={"demo": {"source": "installed"}}):
            with self.assertRaisesRegex(ValueError, "usage-only"):
                loop.next_round(self.root, self.root / "next", self.case_path)
        self.assertFalse((self.root / "next").exists())

    def test_operational_pause_prevents_budget_reservation(self):
        from eval_contracts import execution_preflight

        with (
            patch.object(loop, "execution_preflight", side_effect=execution_preflight),
            patch.object(loop.subprocess, "run") as run,
        ):
            with self.assertRaisesRegex(ValueError, "実評価は停止中"):
                loop.launch(self.plan, self.root)
            run.assert_not_called()
        self.assertFalse((self.root / "started.json").exists())

    def test_isolated_execution_requires_exact_opt_in(self):
        from eval_contracts import execution_preflight

        for value in ("", "0", "true"):
            with patch.dict(os.environ, {"SKILL_EVAL_ISOLATED_RUN": value}):
                with self.assertRaises(ValueError):
                    execution_preflight()
        with patch.dict(os.environ, {"SKILL_EVAL_ISOLATED_RUN": "1"}):
            execution_preflight()

    def test_missing_alignment_stops_model_execution(self):
        self.plan["cases"][0]["alignment"] = ""
        with patch.object(loop.subprocess, "run") as run:
            with self.assertRaises(ValueError):
                loop.launch(self.plan, self.root)
            run.assert_not_called()
        self.assertFalse((self.root / "started.json").exists())

    def test_budget_and_stale_contract_block_execution(self):
        self.plan["max_calls"] = 1
        self.assertTrue(loop.validate(self.plan))
        self.plan["max_calls"] = 2
        self.plan["cases"][0]["contract_version"] = "old"
        self.assertTrue(loop.validate(self.plan))

    def test_complete_screen_is_not_adoption_evidence(self):
        with patch.object(loop, "reviewed_result", side_effect=lambda x: x):
            plan = self.reviewed(self.results())
            self.assertEqual(loop.validate(plan, "review"), [])
            self.assertEqual(loop.validate(plan, "decision"), [])
            plan = self.reviewed(self.results(), "keep")
            self.assertTrue(loop.validate(plan, "decision"))

    def test_partial_duplicate_mixed_and_ungraded_results_block_review(self):
        base = self.results()
        variants = [base[:1], base + base[:1]]
        for field, value in [
            ("success", None),
            ("agent_version", "2"),
            ("failure_kind", "timeout"),
            ("experiment_id", "another"),
        ]:
            changed = copy.deepcopy(base)
            changed[0][field] = value
            variants.append(changed)
        with patch.object(loop, "reviewed_result", side_effect=lambda x: x):
            for items in variants:
                with self.subTest(items=items):
                    self.assertTrue(loop.validate(self.reviewed(items), "review"))

    def test_changed_plan_after_run_is_rejected(self):
        with patch.object(loop, "reviewed_result", side_effect=lambda x: x):
            plan = self.reviewed(self.results())
            plan["purpose"] = "Different purpose"
            self.assertTrue(loop.validate(plan, "review"))

    def test_candidate_requires_diagnosis_extraction_and_holdout(self):
        self.plan.update(
            mode="validate",
            runs=3,
            max_calls=9,
            candidate={"path": str(self.case_path), "version": "candidate"},
        )
        with patch.object(loop, "tree_version", return_value="candidate"):
            errors = loop.validate(self.plan)
        self.assertTrue(any("script_review" in e for e in errors))
        self.assertTrue(any("diagnosis" in e for e in errors))
        self.assertTrue(any("holdout" in e for e in errors))
        self.assertTrue(any("typical / boundary / negative" in e for e in errors))

    def test_validated_candidate_acceptance_and_holdout_regression(self):
        self.plan.update(
            mode="validate",
            runs=3,
            max_calls=27,
            candidate={"path": str(self.case_path), "version": "candidate"},
            diagnosis={
                "cause": "Unsupported finding",
                "evidence": "trace",
                "change": "Check framework contract",
            },
            script_review={
                "decision": "defer",
                "reason": "Context judgment",
                "input_output": "trace to finding",
                "failure": "unknown evidence",
                "idempotence": "read only",
                "verification": "purpose rubric",
            },
        )
        self.plan["cases"] = []
        for scenario in ("typical", "boundary", "negative"):
            case = dict(self.case, id=scenario, scenario=scenario)
            path = self.root / (scenario + ".json")
            path.write_text(json.dumps(case))
            self.plan["cases"].append(
                {
                    "path": str(path),
                    "contract_version": "version",
                    "alignment": "Tests purpose",
                    "verifier_evidence": "Fixture evidence",
                    "holdout": scenario == "negative",
                }
            )
            items = [
                dict(
                    x,
                    case=scenario,
                    run=run,
                    candidate_version="candidate",
                    success=x["variant"] != "treatment",
                )
                for run in range(1, 4)
                for x in self.results(("control", "treatment", "candidate"))
            ]
            (self.root / (scenario + ".jsonl")).write_text(
                "\n".join(json.dumps(x) for x in items)
            )
        plan = self.reviewed([], "adopt")
        with (
            patch.object(loop, "tree_version", return_value="candidate"),
            patch.object(loop, "reviewed_result", side_effect=lambda x: x),
        ):
            self.assertEqual(loop.validate(plan, "decision"), [])
            path = self.root / "negative.jsonl"
            items = [json.loads(line) for line in path.read_text().splitlines()]
            items[-1]["success"] = False
            path.write_text("\n".join(json.dumps(x) for x in items))
            self.assertTrue(any("adopt:" in e for e in loop.validate(plan, "decision")))

            # Equal quality can qualify only under an execution-frozen efficiency policy.
            for entry in self.plan['cases']:
                case_id = loop.read(pathlib.Path(entry['path']))['id']
                result_path = self.root / (case_id + '.jsonl')
                rows = [json.loads(line) for line in result_path.read_text().splitlines()]
                for row in rows:
                    row.update(success=True, total_tokens=70 if row['variant'] == 'candidate' else 100)
                result_path.write_text('\n'.join(json.dumps(row) for row in rows))
            self.assertTrue(any('adopt:' in e for e in loop.validate(plan, 'decision')))
            self.plan['efficiency'] = dict(metric='total_tokens', minimum_reduction=0.2,
                                          quality_evidence='Independent contract cases', rationale='Worth maintaining')
            plan = self.reviewed([], 'adopt')
            self.assertEqual(loop.validate(plan, 'decision'), [])
            rows[-1]['total_tokens'] = 90
            result_path.write_text('\n'.join(json.dumps(row) for row in rows))
            self.assertTrue(any('adopt:' in e for e in loop.validate(plan, 'decision')))

    def test_completed_run_cannot_be_billed_twice(self):
        with patch.object(loop.subprocess, "run") as run:
            run.return_value.returncode = 0
            loop.launch(self.plan, self.root)
            with self.assertRaises(FileExistsError):
                loop.launch(self.plan, self.root)
            self.assertEqual(run.call_count, 1)

    def test_direct_installed_candidate_is_rejected(self):
        self.plan['candidate'] = {'path': str(self.case_path), 'version': 'candidate'}
        with patch.object(loop, 'load_catalog', return_value={'demo': {'source': 'installed'}}):
            self.assertTrue(any('usage-only' in e for e in loop.validate(self.plan)))

    def test_efficiency_requires_every_pair_quality_and_declared_reduction(self):
        policy = {'metric': 'total_tokens', 'minimum_reduction': 0.2}
        pair = {'treatment': {'success': True, 'total_tokens': 100},
                'candidate': {'success': True, 'total_tokens': 75}}
        self.assertTrue(loop.efficiency_passes(policy, [pair]))
        for measured in (81, None, True, float('nan'), -1):
            other = copy.deepcopy(pair)
            other['candidate']['total_tokens'] = measured
            self.assertFalse(loop.efficiency_passes(policy, [pair, other]))
        pair['candidate']['success'] = False
        self.assertFalse(loop.efficiency_passes(policy, [pair]))
        self.assertFalse(loop.efficiency_passes(None, [pair]))

    def test_interrupted_run_reserves_budget_and_never_auto_retries(self):
        with patch.object(
            loop.subprocess, "run", side_effect=OSError("interrupted")
        ) as run:
            with self.assertRaises(OSError):
                loop.launch(self.plan, self.root)
            with self.assertRaises(FileExistsError):
                loop.launch(self.plan, self.root)
            self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()

class HumanReviewTest(unittest.TestCase):
    def test_ai_missing_and_stale_review_cannot_authorize_decision(self):
        pairs = [{'control': {'artifact_version': 'a'}, 'treatment': {'artifact_version': 'b'}}]
        decision = {'action':'keep'}
        self.assertTrue(loop.human_review_errors(decision, pairs))
        decision['human_review'] = {'kind':'ai','action':'keep','reviewer':'AI','evidence':'example','conclusion':'keep','artifact_versions':['a','b']}
        self.assertTrue(loop.human_review_errors(decision, pairs))
        decision['human_review']['kind']='human'
        self.assertEqual(loop.human_review_errors(decision, pairs), [])
        decision['human_review']['artifact_versions']=['old']
        self.assertTrue(loop.human_review_errors(decision, pairs))
