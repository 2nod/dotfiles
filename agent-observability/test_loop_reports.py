import json
from pathlib import Path
import tempfile
import unittest

from eval_contracts import tree_version
from loop_reports import review_template, save_review, report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.artifact = self.root / 'artifact'
        (self.artifact / 'after').mkdir(parents=True)
        (self.artifact / 'after/result.md').write_text('Real output')
        (self.artifact / 'trace.jsonl').write_text('{}\n')
        self.row = {'case': 'normal', 'run': 1, 'variant': 'treatment',
                    'failure_kind': 'passed', 'success': None,
                    'artifact_version': tree_version(self.artifact),
                    'artifacts': str(self.artifact), 'total_tokens': 20,
                    'duration_seconds': 1.5,
                    'rubric': [{'id': 'outcome', 'criterion': 'Read actual output'}]}
        case = self.root / 'case.json'
        case.write_text(json.dumps({'id': 'normal'}))
        self.plan = {'skill': 'sample', 'runs': 1, 'cases': [{'path': str(case)}]}
        (self.root / 'normal.jsonl').write_text(json.dumps(self.row)+'\n')
        self.review = self.root / 'scores.json'

    def scores(self):
        d = review_template(self.row)
        d['reviewer'] = 'Human non-blind'
        d['criteria'][0].update({'pass': True, 'evidence': 'after/result.md and trace inspected'})
        self.review.write_text(json.dumps(d))

    def test_ungraded_output_is_not_success_and_review_enables_it(self):
        state = {'state': 'needs-review', 'next_action': 'inspect'}
        result = report(self.root, self.plan, state)
        self.assertEqual(result['ungraded'], 1)
        d = json.loads((self.root / 'report.json').read_text())
        self.assertEqual(d['summary'][1]['passed'], 0)
        self.assertEqual(d['expected_results'], 2)
        self.scores()
        self.assertTrue(save_review(self.row, self.review)['success'])
        self.assertEqual(report(self.root, self.plan, state)['ungraded'], 0)
        with self.assertRaises(ValueError):
            save_review(self.row, self.review)

    def test_template_is_incomplete_and_tampering_rejects_scores(self):
        self.review.write_text(json.dumps(review_template(self.row)))
        with self.assertRaises(ValueError):
            save_review(self.row, self.review)
        self.assertFalse((self.artifact / 'review.json').exists())
        self.scores()
        (self.artifact / 'after/result.md').write_text('Changed after grading')
        with self.assertRaises(ValueError):
            save_review(self.row, self.review)
        self.assertFalse((self.artifact / 'review.json').exists())

    def test_review_never_overrides_failed_execution(self):
        self.scores()
        self.row.update(failure_kind='verifier_failed', success=False)
        with self.assertRaises(ValueError):
            save_review(self.row, self.review)
        self.assertFalse((self.artifact / 'review.json').exists())

    def test_runner_created_empty_review_can_be_completed(self):
        target = self.artifact / 'review.json'
        target.write_text(json.dumps(review_template(self.row)))
        self.scores()
        self.assertTrue(save_review(self.row, self.review)['success'])

    def comparison(self, control=False, candidate=True):
        self.plan.update(candidate={"path": "candidate", "version": "candidate-version"},
                         model="fixed/model", purpose="Preserve behavior with fewer reads",
                         scope="Synthetic only", diagnosis={"change": "Drop irrelevant reference"},
                         efficiency={"metric": "total_tokens", "minimum_reduction": 0.2})
        rows = []
        for variant, success, tokens in (("control", control, 100), ("treatment", True, 100), ("candidate", candidate, 70)):
            artifact = self.root / variant
            (artifact / "after").mkdir(parents=True)
            (artifact / "after/result.md").write_text("result " + variant)
            (artifact / "trace.jsonl").write_text("{}\n")
            row = dict(self.row, variant=variant, artifacts=str(artifact), total_tokens=tokens,
                       artifact_version=tree_version(artifact), model="fixed/model", agent="pi", agent_version="fixed")
            review = review_template(row)
            review['reviewer'] = 'AI synthetic non-blind'
            review['criteria'][0]['pass'] = success
            review['criteria'][0]['evidence'] = 'after/result.md: observed contract'
            (artifact / 'review.json').write_text(json.dumps(review))
            rows.append(row)
        (self.root / 'normal.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))
        return rows

    def test_failed_control_does_not_block_current_candidate_efficiency(self):
        from comparison_checks import comparison_pairs, efficiency_passes
        self.comparison()
        report(self.root, self.plan, {'state': 'needs-decision', 'next_action': 'record-decision'})
        data = json.loads((self.root / 'report.json').read_text())
        self.assertTrue(data['efficiency_comparison_ready'])
        self.assertTrue(data['comparison']['threshold_met'])
        self.assertEqual(data['comparison']['threshold_met'], efficiency_passes(self.plan['efficiency'], comparison_pairs(data['results'])))
        self.assertFalse(data['decision_valid'])
        md = (self.root / 'report.md').read_text()
        self.assertIn('fixed/model', md)
        self.assertIn('Drop irrelevant reference', md)
        self.assertIn('AI synthetic non-blind', md)
        self.assertIn('未確定', md)
        self.assertIn('trace.jsonl', md)

    def test_failed_candidate_and_tampered_artifacts_block_efficiency(self):
        rows = self.comparison(candidate=False)
        report(self.root, self.plan, {'state': 'needs-decision', 'next_action': 'record-decision'})
        self.assertFalse(json.loads((self.root / 'report.json').read_text())['efficiency_comparison_ready'])
        (Path(rows[1]['artifacts']) / 'after/result.md').write_text('Changed')
        report(self.root, self.plan, {'state': 'needs-review', 'next_action': 'review'})
        data = json.loads((self.root / 'report.json').read_text())
        self.assertFalse(data['efficiency_comparison_ready'])
        self.assertEqual(len(data['review_queue']), 1)

    def test_missing_pair_and_invalid_decision_remain_visible(self):
        rows = self.comparison()
        (self.root / 'normal.jsonl').write_text('\n'.join(json.dumps(row) for row in rows[:-1]))
        (self.root / 'decision.json').write_text(json.dumps({'action': 'adopt', 'reason': 'Proposed'}))
        report(self.root, self.plan, {'state': 'needs-review', 'next_action': 'repair', 'errors': ['missing candidate']})
        data = json.loads((self.root / 'report.json').read_text())
        self.assertFalse(data['efficiency_comparison_ready'])
        self.assertFalse(data['decision_valid'])
        self.assertIn('missing candidate', (self.root / 'report.md').read_text())
        self.assertIn('Proposed', (self.root / 'report.md').read_text())
