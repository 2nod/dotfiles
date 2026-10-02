"""A completed contextual review survives refresh, but changed evidence reopens it."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from usage_cases import case_candidates
from usage_reviews import attach_reviews, observation_version, save_review
from test_usage_cases import work


class UsageReviewsTest(unittest.TestCase):
    def test_result_and_design_survive_refresh_without_closing_new_work(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.jsonl'
            source.write_text('request\nresult\n')
            refs = [{'role': role, 'path': str(source), 'line': n,
                     'sha256': hashlib.sha256(text.encode()).hexdigest()}
                    for n, (role, text) in enumerate([('request', 'request'), ('result', 'result')], 1)]
            observed = work('a' * 20)
            observed['evidence'] = [{k:v for k,v in ref.items() if k != 'role'} for ref in refs]
            record = {'observation': observed, 'observation_version': observation_version(observed),
                      'reviewer': {'kind': 'ai', 'name': 'sample'}, 'conversation_evidence': refs,
                      'assessment': {'context': 'real_work', 'reason': 'Original failure was repaired.'},
                      'result': {'outcome': 'recovered', 'summary': 'Regression fixed; later checks passed.'},
                      'design': {'action': 'no_case', 'reason': 'Existing regression already covers the behavior.',
                                 'next_action': 'Retain the current check.'}}
            invalid = copy.deepcopy(record)
            invalid['design']['reason'] = None
            with self.assertRaises(ValueError):
                save_review(root, invalid, [observed])
            path = save_review(root, record, [observed])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            replica = copy.deepcopy(observed)
            replica['evidence'].append({**replica['evidence'][0], 'path': 'replicated-home/source.jsonl'})
            self.assertEqual(observation_version(replica), observation_version(observed))
            fresh = [copy.deepcopy(observed), work('b' * 20)]
            self.assertEqual(attach_reviews(root, fresh), {'reviewed': 1, 'pending': 1})
            self.assertEqual(fresh[0]['work_verification'], 'reported_failed')
            self.assertEqual(fresh[0]['case_review']['result']['outcome'], 'recovered')
            group = case_candidates(fresh, {'guide': {}}, [])[0]
            self.assertEqual(group['reviewed_work_count'], 1)
            self.assertEqual(group['work_count'], 2)
            self.assertEqual(group['reviewed_examples'], ['a' * 20])
            changed = copy.deepcopy(observed)
            changed['work_verification'] = 'reported_passed'
            self.assertEqual(attach_reviews(root, [changed]), {'needs_review': 1})
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                save_review(root, record, [changed])
            self.assertEqual(path.read_bytes(), original)
            source.write_text('request\nchanged result\n')
            self.assertEqual(attach_reviews(root, [copy.deepcopy(observed)]), {'needs_review': 1})
            self.assertEqual(path.read_bytes(), original)
            path.write_text('{}')
            self.assertEqual(attach_reviews(root, [copy.deepcopy(observed)]), {'needs_review': 1})

    def test_linked_case_contract_change_requires_design_review(self):
        from eval_contracts import contract_version
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'fixture').mkdir()
            (root / 'skill').mkdir()
            (root / 'skill/SKILL.md').write_text('A synthetic guide.')
            source = root / 'source'
            source.write_text('evidence\n')
            observed = work('c' * 20)
            observed['evidence'] = [{'path': str(source), 'line': 1,
                                     'sha256': hashlib.sha256(b'evidence').hexdigest()}]
            case = {'id': 'sample', 'skill': 'guide', 'skill_path': 'skill/SKILL.md', 'fixture': 'fixture',
                    'evaluation': {'status': 'ready'}, 'rubric': [{'id': 'purpose', 'criterion': 'Check behavior'}],
                    'verifiers': [['python3', '-c', 'print(1)']]}
            case_path = root / 'case.json'
            case_path.write_text(json.dumps(case))
            record = {'observation': observed, 'observation_version': observation_version(observed),
                      'reviewer': {'kind': 'ai', 'name': 'sample'},
                      'conversation_evidence': [{'role': role, 'path': str(source), 'line': 1,
                                                'sha256': hashlib.sha256(b'evidence').hexdigest()} for role in ('request','result')],
                      'assessment': {'context': 'real_work', 'reason': 'Inspected the source.'},
                      'result': {'outcome': 'recovered', 'summary': 'Repaired.'},
                      'design': {'action': 'reuse_case', 'reason': 'Same behavior.', 'problem': 'Problem',
                                 'expected_behavior': 'Expected', 'next_action': 'Compare only with specified model.',
                                 'case': {'path': str(case_path), 'contract_version': contract_version(case, case_path),
                                          'verification_evidence': 'Only structure checked; model effect not measured.'}}}
            save_review(root, record, [observed])
            self.assertEqual(attach_reviews(root, [copy.deepcopy(observed)]), {'reviewed': 1})
            (root / 'fixture/new.txt').write_text('changed')
            fresh = copy.deepcopy(observed)
            self.assertEqual(attach_reviews(root, [fresh]), {'needs_review': 1})
            self.assertIn('case design changed', fresh['case_review']['reason'])


if __name__ == '__main__':
    unittest.main()
