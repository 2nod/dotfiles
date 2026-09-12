"""Synthetic trace checks, never model output quality claims."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from behavior_checks import check_behavior

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('behavior_runner', ROOT / 'evaluate-skill.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def trace(calls, failed=False):
    events = []
    for i, (name, args) in enumerate(calls):
        events.append({'type': 'tool_execution_start', 'toolName': name, 'toolCallId': str(i), 'args': args})
        events.append({'type': 'tool_execution_end', 'toolName': name, 'toolCallId': str(i), 'isError': failed, 'result': {'isError': failed}})
    return '\n'.join(json.dumps(event) for event in events)


class BehaviorTests(unittest.TestCase):
    def test_catalog_exposes_metadata_without_forcing_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / 'SKILL.md'
            skill.write_text('---\nname: sample\ndescription: Edit a sample.\n---\nPRIVATE BODY MARKER')
            case = {'skill_dependencies': {}}
            entries = runner.skill_catalog(case, root / 'case.json', skill, 'treatment', '/skills')
            command = runner.pi_command('Fix sample', skill, 'fixed/model', catalog=entries)
            text = ' '.join(command)
            self.assertIn('Edit a sample.', text)
            self.assertNotIn('PRIVATE BODY MARKER', text)
            self.assertNotIn('Apply this skill', text)
            self.assertEqual(runner.skill_catalog(case, root / 'case.json', skill, 'control', '/skills'), [])
            self.assertIn('PRIVATE BODY MARKER', ' '.join(runner.pi_command('Fix sample', skill, 'fixed/model')))

    def test_dry_run_uses_the_same_catalog_command_as_execution(self):
        path = ROOT.parent / '.agents/evals/behavior-scout-unrelated-edit.json'
        result = subprocess.run([sys.executable, str(ROOT / 'evaluate-skill.py'), str(path), '--runs', '1', '--dry-run'], text=True, capture_output=True, check=True)
        preview = json.loads(result.stdout)
        case = runner.load_case(path)
        target = runner.resolve_case_path(path, case['skill_path'])
        self.assertEqual(preview['invocation'], 'catalog')
        self.assertEqual(preview['treatment_command'], runner.case_command(case, path, target, 'treatment', None))
        self.assertNotIn('Apply this skill', ' '.join(preview['treatment_command']))

    def test_relevant_read_and_completion_required(self):
        rules = {'required_reads': ['/workspace/README.md'], 'forbidden_reads': ['/skills/references/deploy.md'],
                 'files': {'README.md': 'fixed'}, 'unchanged_except': ['README.md']}
        before = {'README.md': b'broken', 'keep.txt': b'keep'}
        after = {**before, 'README.md': b'fixed'}
        events = [('read', {'path': 'README.md'}), ('edit', {'path': 'README.md'})]
        self.assertTrue(check_behavior(rules, trace(events), before, after)['passed'])
        for observed, result in ((trace(events), before), ('', after),
                                 (trace(events + [('read', {'path': '/skills/references/deploy.md'})]), after),
                                 (trace(events + [('bash', {'command': 'cat /skills/references/deploy.md'})]), after),
                                 (trace(events), {**after, 'keep.txt': b'changed'})):
            self.assertFalse(check_behavior(rules, observed, before, result)['passed'])

    def test_verification_must_finish_successfully_not_just_be_mentioned(self):
        rules = {'required_bash': ['python3 verify.py']}
        calls = [('bash', {'command': 'python3 verify.py'})]
        self.assertTrue(check_behavior(rules, trace(calls), {}, {})['passed'])
        self.assertFalse(check_behavior(rules, trace(calls, failed=True), {}, {})['passed'])
        self.assertFalse(check_behavior(rules, 'I ran python3 verify.py', {}, {})['passed'])
        self.assertFalse(check_behavior(rules, trace(calls).splitlines()[0], {}, {})['passed'])

    def test_all_behavior_fixtures_fail_before_and_pass_after_minimal_change(self):
        cases = ROOT.parent / '.agents/evals'
        for path in sorted(cases.glob('behavior-*.json')):
            with self.subTest(case=path.name), tempfile.TemporaryDirectory() as tmp:
                case = runner.load_case(path)
                fixture = cases / case['fixture']
                before = {p.relative_to(fixture).as_posix(): p.read_bytes() for p in fixture.rglob('*') if p.is_file()}
                after = {**before, **{p: text.encode() for p, text in case['behavior']['files'].items()}}
                calls = [('read', {'path': pattern}) for pattern in case['behavior'].get('required_reads', [])]
                calls += [('edit', {'path': p}) for p in case['behavior']['files']]
                calls += [('bash', {'command': command}) for command in case['behavior'].get('required_bash', [])]
                self.assertFalse(check_behavior(case['behavior'], '', before, before)['passed'])
                self.assertTrue(check_behavior(case['behavior'], trace(calls), before, after)['passed'])
                work = Path(tmp)
                command = [sys.executable, str(cases / 'behavior-artifact-verify.py'), str(work), str(path)]
                for content, expected_exit in ((before, 1), (after, 0)):
                    for name, data in content.items():
                        dest = work / name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(data)
                    self.assertEqual(subprocess.run(command).returncode, expected_exit)
