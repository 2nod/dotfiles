"""Offline CLI lifecycle against real saved artifacts; no inference or credentials."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from eval_contracts import contract_version

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cli_evaluator', ROOT / 'evaluate-skill.py')
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


class CliLifecycleTest(unittest.TestCase):
    def test_init_requires_model_and_selects_only_requested_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'round'
            command = [sys.executable, str(ROOT / 'skill-loop.py'), 'init', str(root), '--skill', 'skill-maintenance']
            missing = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(missing.returncode, 1)
            self.assertFalse(root.exists())
            result = subprocess.run([*command, '--model', 'offline/stub', '--invocation', 'catalog'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads((root / 'plan.json').read_text())
            self.assertEqual(plan['model'], 'offline/stub')
            self.assertEqual(len(plan['cases']), 2)
            self.assertTrue(all(json.loads(Path(entry['path']).read_text())['invocation'] == 'catalog' for entry in plan['cases']))
            self.assertFalse((root / 'started.json').exists())
            plan['invocation'] = 'explicit'
            (root / 'plan.json').write_text(json.dumps(plan))
            mismatch = subprocess.run([sys.executable, str(ROOT / 'skill-loop.py'), 'check', str(root)], capture_output=True, text=True)
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn('計画とケースの呼び出し方法が不一致', mismatch.stdout + mismatch.stderr)

    def test_prepare_review_report_decide_continue_and_reject_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            round_dir = root / 'round'
            cli = [sys.executable, str(ROOT / 'skill-loop.py')]

            def call(command, *args, ok=True):
                result = subprocess.run([*cli, command, str(round_dir), *args],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0 if ok else 1, result.stderr + result.stdout)
                return result

            call('init', '--skill', 'skill-maintenance', '--model', 'offline/stub')
            self.assertEqual(json.loads(call('status').stdout)['state'], 'needs-plan')
            fixture = root / 'fixture'
            fixture.mkdir()
            (fixture / 'input.txt').write_text('Produce synthetic result')
            (root / 'skill').mkdir()
            skill = root / 'skill/SKILL.md'
            skill.write_text('Produce synthetic result')
            case = {'id': 'offline', 'skill': 'skill-maintenance',
                    'skill_path': 'skill/SKILL.md', 'fixture': 'fixture',
                    'verifiers': [], 'scenario': 'typical',
                    'evaluation': {'status': 'ready'},
                    'rubric': [{'id': 'output', 'criterion': 'Correct synthetic result'}]}
            path = root / 'case.json'
            path.write_text(json.dumps(case))
            plan = json.loads((round_dir / 'plan.json').read_text())
            plan.update(scope='Offline saved-output lifecycle, no inference', reviewer='Test non-blind',
                        max_calls=2, cases=[{'path': str(path), 'contract_version': contract_version(case, path),
                                            'alignment': 'Normal output', 'verifier_evidence': 'Synthetic test',
                                            'holdout': False}])
            (round_dir / 'plan.json').write_text(json.dumps(plan))
            call('check')
            self.assertEqual(json.loads(call('status').stdout)['state'], 'ready')
            # The launch reservation and Docker execution have separate boundary tests.
            # Here exercise the actual CLI over the runner's artifact format.
            (round_dir / 'started.json').write_text(json.dumps(plan))
            rows = []
            with patch.object(evaluator, 'ROOT', root / 'runtime'):
                for variant in ('control', 'treatment'):
                    artifact, version = evaluator.persist_artifacts(
                        case, {}, {'result.md': b'synthetic result'}, '{}\n', '', 'offline', 1, variant)
                    rows.append({'case': 'offline', 'variant': variant, 'run': 1,
                                 'model': 'offline/stub', 'agent': 'pi', 'agent_version': 'offline',
                                 'experiment_id': 'offline', 'contract_version': contract_version(case, path),
                                 'rubric': case['rubric'], 'artifacts': artifact, 'artifact_version': version,
                                 'failure_kind': 'passed', 'success': None})
            (round_dir / 'offline.jsonl').write_text('\n'.join(map(json.dumps, rows)))
            (round_dir / 'completed.json').write_text('{}')
            self.assertEqual(json.loads(call('report').stdout)['ungraded'], 2)
            call('check', '--stage', 'review', ok=False)
            for variant in ('control', 'treatment'):
                selector = ['--case', 'offline', '--run', '1', '--variant', variant]
                review = json.loads(call('review-template', *selector).stdout)
                review['reviewer'] = 'Offline test non-blind'
                review['criteria'][0].update({'pass': True, 'evidence': 'after/result.md: synthetic result; trace: offline'})
                scores = root / 'scores.json'
                scores.write_text(json.dumps(review))
                call('review', *selector, '--review-file', str(scores))
            call('check', '--stage', 'review')
            self.assertEqual(json.loads(call('status').stdout)['state'], 'needs-decision')
            decision = dict(action='hold', reason='Same result', evidence='both outputs', reviewer='Test',
                            limitations='No inference', next_check='Independent scenario')
            (round_dir / 'decision.json').write_text(json.dumps(decision))
            call('check', '--stage', 'decision')
            self.assertEqual(json.loads(call('report').stdout)['state'], 'decided')
            destination = root / 'next'
            call('next', '--to', str(destination))
            next_plan = json.loads((destination / 'plan.json').read_text())
            self.assertEqual(next_plan['lineage']['parent_decision'], decision)
            self.assertFalse((destination / 'started.json').exists())
            next_plan['scope'] = 'Recheck'
            next_plan['cases'][0]['holdout'] = True
            (destination / 'plan.json').write_text(json.dumps(next_plan))
            result = subprocess.run([*cli, 'check', str(destination)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('holdout', result.stdout)
            (Path(rows[0]['artifacts']) / 'after/result.md').write_text('Changed')
            call('check', '--stage', 'review', ok=False)
            self.assertEqual(json.loads(call('status').stdout)['state'], 'needs-review')
