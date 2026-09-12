import tempfile
from pathlib import Path
import unittest
from skill_current_state import deployment_state, decision_state, collect_rounds

class CurrentSkillStateTest(unittest.TestCase):
    def test_bundle_difference_and_missing_deployment(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'source', Path(tmp)/'deployed'
            for p in (a,b):
                p.mkdir(); (p/'SKILL.md').write_text('same')
            location = ((b/'SKILL.md').as_uri(), 'shared', 'authored')
            self.assertIn('一致', deployment_state(a/'SKILL.md', location))
            (b/'reference.md').write_text('extra')
            self.assertIn('不一致', deployment_state(a/'SKILL.md', location))
            self.assertIn('見つかりません', deployment_state(a/'SKILL.md', None))
            (a/'SKILL.md').unlink()
            self.assertIn('履歴のみ', deployment_state(a/'SKILL.md', location))

    def test_invalid_evidence_never_becomes_adoption(self):
        row = {'state': {'state': 'needs-review'}, 'decision': {'action':'adopt'}}
        self.assertEqual(decision_state([row]), ('判断材料不足', []))
        row['state']['state'] = 'decided'
        self.assertIn('採用判断あり', decision_state([row])[0])
        opposing = {'state': {'state': 'decided'}, 'decision': {'action':'disable'}}
        self.assertIn('競合', decision_state([row, opposing])[0])

    def test_bad_round_is_reported_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); d=root/'eval-loops'/'broken'; d.mkdir(parents=True)
            (d/'plan.json').write_text('{')
            def broken(path): raise ValueError('bad plan')
            rows = collect_rounds(root, broken)
            self.assertEqual(rows[0]['state']['state'], 'invalid')
            self.assertEqual((d/'plan.json').read_text(), '{')
