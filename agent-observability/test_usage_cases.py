"""Candidate preparation must keep observed signals separate from case correctness."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from usage_cases import case_candidates, load_cases, save_candidates


def work(identifier, *, skills=('guide',), outcome='reported_failed', reasons=('verification_failed',), ended=True):
    return {'id': identifier, 'skills': [{'name': name} for name in skills],
            'work_verification': outcome, 'review_reasons': list(reasons),
            'ended_at': '2030-01-02T01:00:00+00:00' if ended else None,
            'started_at': '2030-01-02T00:00:00+00:00', 'agent': 'codex', 'observed_models': ['sample']}


class UsageCasesTest(unittest.TestCase):
    def test_completed_examples_do_not_hide_pending_or_changed_work(self):
        observations = [work(str(n)) for n in range(6)]
        for n, observed in enumerate(observations):
            observed['started_at'] = f'2030-01-0{n + 1}T00:00:00+00:00'
        for observed in observations[3:]:
            observed['case_review'] = {'state': 'reviewed'}
        observations[1]['case_review'] = {'state': 'needs_review'}
        group = case_candidates(observations, {'guide': {}}, [])[0]
        self.assertEqual(group['examples'], ['2', '1', '0'])
        self.assertEqual(group['reviewed_examples'], ['5', '4', '3'])
        observations[2]['case_review'] = {'state': 'reviewed'}
        group = case_candidates(observations, {'guide': {}}, [])[0]
        self.assertEqual(group['examples'], ['1', '0'])
        for observed in observations:
            observed['case_review'] = {'state': 'reviewed'}
        group = case_candidates(observations, {'guide': {}}, [])[0]
        self.assertEqual(group['status'], 'reviewed')
        self.assertEqual(group['examples'], [])

    def test_reviewed_groups_do_not_hide_pending_groups_in_a_shortlist(self):
        done = work('done', skills=('done',))
        done['case_review'] = {'state': 'reviewed'}
        pending = work('pending', skills=('pending',), outcome='unverified', reasons=())
        groups = case_candidates([done, pending], {'done': {}, 'pending': {}}, [])
        self.assertEqual(groups[0]['examples'], ['pending'])
        self.assertEqual(groups[1]['status'], 'reviewed')

    def test_grouping_keeps_counterexamples_and_does_not_claim_semantic_coverage(self):
        observations = [work('failure', skills=('guide', 'helper', 'unknown')),
                        work('failure-two'), work('open', ended=False),
                        work('ordinary', outcome='unverified', reasons=()),
                        work('success', outcome='reported_passed', reasons=()),
                        work('uncertain', outcome='unverified', reasons=('verification_result_unconfirmed',))]
        catalog = {'guide': {}, 'helper': {}}
        cases = [{'id': 'existing', 'skill': 'guide', 'scenario': 'boundary', 'design_status': 'ready'},
                 {'id': 'old', 'skill': 'guide', 'scenario': 'negative', 'design_status': 'legacy'}]
        groups = case_candidates(observations, catalog, cases)
        self.assertEqual({group['signal'] for group in groups[:4]},
                         {'verification_failed', 'verification_unconfirmed', 'verification_passed', 'usage_observed'})
        guide = next(g for g in groups if g['skill'] == 'guide' and g['signal'] == 'verification_failed')
        self.assertEqual(guide['work_count'], 2)
        self.assertEqual(guide['co_used_work_count'], 1)
        self.assertEqual(guide['case_match'], 'unassessed')
        self.assertEqual(guide['missing_scenarios'], ['negative', 'typical'])
        self.assertEqual(guide['related_cases'], cases)
        self.assertNotIn('unknown', [group['skill'] for group in groups])
        self.assertNotIn('open', [id for group in groups for id in group['examples']])
        self.assertEqual(groups, case_candidates(list(reversed(observations)), catalog, cases))
        selected = case_candidates(observations, catalog, cases, 'guide')
        self.assertEqual({group['skill'] for group in selected}, {'guide'})
        refreshed = case_candidates(observations + [work('new-failure')], catalog, cases)
        self.assertEqual(guide['id'], next(g['id'] for g in refreshed if g['skill'] == 'guide' and g['signal'] == 'verification_failed'))

    def test_bad_catalog_is_visible_and_snapshot_is_private_atomic_and_separate_from_reviews(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(load_cases(root / 'missing')[1][0]['reason'], 'directory_unavailable')
            (root / 'broken.json').write_text('{}')
            self.assertEqual(load_cases(root)[1][0]['file'], 'broken.json')
            (root / 'bad-scenario.json').write_text(json.dumps({'id': 'bad', 'skill': 'guide', 'scenario': []}))
            self.assertEqual(len(load_cases(root)[1]), 2)
            report = {'generated_at': '2030-01-02', 'window_start': '2030-01-01', 'source': 'native', 'selected_skill': None,
                      'evaluation_candidates': [], 'case_catalog_errors': []}
            reviews = root / 'usage-reviews'
            reviews.mkdir()
            (reviews / 'review.json').write_text('USER_REVIEW')
            path = save_candidates(root, report)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            before = path.read_bytes()
            with patch('usage_cases.Path.replace', side_effect=OSError('disk error')):
                with self.assertRaises(OSError):
                    save_candidates(root, {**report, 'generated_at': 'later'})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(root.glob('.eval-candidates-*')), [])
            self.assertEqual((reviews / 'review.json').read_text(), 'USER_REVIEW')
            self.assertEqual(json.loads(path.read_text())['evaluation_candidates'], [])


if __name__ == '__main__':
    unittest.main()
