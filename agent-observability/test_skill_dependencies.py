"""Explicit dependency bundles: path layout, isolation and frozen contracts."""
import importlib.util
from pathlib import Path
import tempfile
import os
import shutil
from isolated_tools import ToolSandbox
import unittest
from unittest.mock import Mock
from eval_contracts import contract_version, dependency_paths

spec = importlib.util.spec_from_file_location('eval_runner', Path(__file__).with_name('evaluate-skill.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class Dependencies(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ['primary', 'guide', 'fixture']:
            (self.root/name).mkdir()
        self.target = self.root/'primary/SKILL.md'
        self.target.write_text('Read ../guide/SKILL.md')
        (self.root/'guide/SKILL.md').write_text('Synthetic reference')
        self.case = {'skill_path':str(self.target), 'fixture':'fixture', 'verifiers':[], 'skill_dependencies':{'guide':'guide'}}
        self.path = self.root/'case.json'

    def test_treatment_has_relative_sibling_and_control_has_none(self):
        worker = Mock()
        location = runner.load_case_skills(worker, self.case, self.path, self.target, 'treatment')
        self.assertEqual(location, '/skills/primary')
        data = worker.load_readonly.call_args.args[0]
        self.assertEqual(data['primary/SKILL.md'], b'Read ../guide/SKILL.md')
        self.assertEqual(data['guide/SKILL.md'], b'Synthetic reference')
        self.assertEqual(set(data), {'primary/SKILL.md','guide/SKILL.md'})
        worker.reset_mock()
        runner.load_case_skills(worker,self.case,self.path,self.target,'control')
        self.assertEqual(worker.mock_calls, [])
        prompt = runner.pi_command('task', self.target, 'model', location)
        self.assertIn('/skills/primary/SKILL.md', ' '.join(prompt))

    def test_dependency_edits_invalidate_contract(self):
        before = contract_version(self.case, self.path)
        (self.root/'guide/SKILL.md').write_text('Changed reference')
        self.assertNotEqual(before, contract_version(self.case, self.path))

    def test_bad_names_and_missing_dependency_fail(self):
        for name in ['../escape', '/absolute', 'primary', '.', '']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                dependency_paths({**self.case,'skill_dependencies':{name:'guide'}},self.path,self.target)
        (self.root/'guide/SKILL.md').unlink()
        with self.assertRaises(ValueError):
            dependency_paths(self.case,self.path,self.target)

    def test_dependency_alias_rejected_before_loading(self):
        (self.root/'guide/alias').symlink_to(self.target)
        worker = Mock()
        with self.assertRaises(ValueError):
            runner.load_case_skills(worker,self.case,self.path,self.target,'treatment')
        self.assertEqual(worker.mock_calls, [])

    def test_legacy_layout_unchanged(self):
        case = dict(self.case); del case['skill_dependencies']
        worker = Mock()
        self.assertEqual(runner.load_case_skills(worker,case,self.path,self.target,'treatment'),'/skills')
        worker.load_skill.assert_called_once_with(self.target.parent)
        worker.load_readonly.assert_not_called()

@unittest.skipUnless(os.environ.get('SKILL_EVAL_OFFLINE_DOCKER') == '1', 'offline Docker opt-in required')
class DockerDependencies(Dependencies):
    def test_real_relative_read_and_control_isolation(self):
        with ToolSandbox(shutil.which('docker')) as worker:
            root = runner.load_case_skills(worker,self.case,self.path,self.target,'treatment')
            self.assertEqual(worker.read(root+'/../guide/SKILL.md'), b'Synthetic reference')
            self.assertNotEqual(worker.bash('echo changed > /skills/guide/SKILL.md').returncode,0)
        with ToolSandbox(shutil.which('docker')) as worker:
            runner.load_case_skills(worker,self.case,self.path,self.target,'control')
            self.assertEqual(worker.bash('test ! -e /skills/guide/SKILL.md && test ! -e /skills/primary/SKILL.md').returncode,0)

if __name__ == '__main__': unittest.main()
