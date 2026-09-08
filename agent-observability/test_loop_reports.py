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
