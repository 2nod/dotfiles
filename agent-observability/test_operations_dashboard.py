import importlib.util
from pathlib import Path
import sys
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
            self.assertIn('記録を読めません', output)
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
