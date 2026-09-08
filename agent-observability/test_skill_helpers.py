"""Synthetic checks for the deterministic parts of authored skill improvements."""
import importlib.util
from pathlib import Path
import shutil
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / '.agents/skills'


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inv = load('inventory_helper', 'agent-management/skill-maintenance/scripts/check_inventory.py')
motion = load('motion_helper', 'software-development/technical-flow-diagrams/scripts/motion_window.py')


class SkillHelpersTest(unittest.TestCase):
    def test_inventory_detects_equal_count_replacement_and_stale_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source/category/demo'
            source.mkdir(parents=True)
            (source / 'SKILL.md').write_text('name: demo')
            (source / 'reference.md').write_text('current')
            target = root / 'target/demo'
            shutil.copytree(source, target)
            expected = inv.inventory([root / 'source'])
            self.assertFalse(any(inv.compare(expected, inv.inventory([root / 'target'])).values()))
            (target / 'reference.md').write_text('stale')
            self.assertEqual(inv.compare(expected, inv.inventory([root / 'target']))['changed'], ['demo'])
            target.rename(root / 'target/other')
            diff = inv.compare(expected, inv.inventory([root / 'target']))
            self.assertEqual(diff['missing'], ['demo'])
            self.assertEqual(diff['extra'], ['other'])

    def test_inventory_supports_deployed_symlinks_and_rejects_cycles(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source/demo'
            source.mkdir(parents=True)
            (source / 'SKILL.md').write_text('name: demo')
            target = root / 'target'
            target.mkdir()
            (target / 'demo').symlink_to(source, target_is_directory=True)
            self.assertEqual(inv.inventory([root / 'source']), inv.inventory([target]))
            (source / 'cycle').symlink_to(source, target_is_directory=True)
            with self.assertRaises(ValueError):
                inv.inventory([target])
        with self.assertRaises(ValueError):
            inv.inventory([root / 'missing'])

    def test_motion_keeps_two_legs_and_wait_in_one_cycle(self):
        first = motion.window(6, 0, 2.16)
        second = motion.window(6, 3.48, 5.64)
        self.assertEqual(first['motion']['begin'], second['motion']['begin'])
        self.assertEqual(first['motion']['dur'], '6s')
        self.assertEqual(second['motion']['dur'], '6s')
        self.assertEqual(first['motion']['keyTimes'], '0;0.36;1')
        self.assertEqual(second['motion']['keyTimes'], '0;0.58;0.94;1')
        self.assertEqual(first['opacity']['values'], '1;0;0')
        self.assertEqual(second['opacity']['values'], '0;1;0;0')
        def position(attributes, seconds):
            time = (seconds - float(attributes['begin'][:-1])) / float(attributes['dur'][:-1])
            times = list(map(float, attributes['keyTimes'].split(';')))
            points = list(map(float, attributes['keyPoints'].split(';')))
            for i in range(1, len(times)):
                if time <= times[i]:
                    fraction = (time - times[i - 1]) / (times[i] - times[i - 1])
                    return points[i - 1] + fraction * (points[i] - points[i - 1])
            return points[-1]

        self.assertAlmostEqual(position(first['motion'], 1.08), 0.5)
        self.assertAlmostEqual(position(first['motion'], 3), 1)
        self.assertAlmostEqual(position(second['motion'], 3), 0)
        self.assertAlmostEqual(position(second['motion'], 4.56), 0.5)
        full = motion.window(6, 0, 6)
        self.assertEqual(full['motion']['keyTimes'], '0;1')
        self.assertEqual(full['opacity']['values'], '1;0')

    def test_motion_rejects_invalid_windows(self):
        for args in [(6, 2, 2), (0, 0, 0), (6, -1, 2), (6, 1, 7), (float('nan'), 0, 1), (6, False, 1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                motion.window(*args)


class WorktreeAuditTests(unittest.TestCase):
    def test_failed_stat_output_does_not_pollute_fallback_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / 'repo'
            subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True)
            binary = root / 'bin'
            binary.mkdir()
            stat = binary / 'stat'
            stat.write_text('#!/bin/sh\nif [ "$1" = "-f" ]; then\n  echo "filesystem diagnostic"\n  exit 1\nfi\nprintf "2026-01-02 03:04:05.000000000 +0000\\n"\n')
            stat.chmod(0o755)
            result = subprocess.run(
                ['bash', str(ROOT / 'software-development/git-worktree-cleanup/scripts/audit-worktrees.sh'), str(repo)],
                env={**os.environ, 'PATH': str(binary) + os.pathsep + os.environ['PATH']},
                capture_output=True, text=True, check=True,
            )
            self.assertNotIn('filesystem diagnostic', result.stdout)
            self.assertIn(' mtime: 2026-01-02 03:04:05\n', result.stdout)


if __name__ == '__main__':
    unittest.main()
