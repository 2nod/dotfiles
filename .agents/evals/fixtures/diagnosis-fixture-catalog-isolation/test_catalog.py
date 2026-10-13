from copy import deepcopy
import unittest
from catalog import fresh_fixture, visible_catalog


class CatalogTest(unittest.TestCase):
    def test_fresh_copy_does_not_pull_obsolete_sessions_but_preserves_source(self):
        old = {'id': 'old-local', 'comparison_group': 'shared-origin',
               'payload': {'source': 'unchanged', 'mask': [[2, 3], [4, 5]]},
               'session': {'head': 'old-head', 'obsolete_notes': ['retained']}}
        before = deepcopy(old)
        first = fresh_fixture(old, 'run-a')
        second = fresh_fixture(old, 'run-b')
        self.assertEqual(visible_catalog(first, [old, first, second]), ['run-a'])
        self.assertEqual(visible_catalog(second, [old, first, second]), ['run-b'])
        self.assertNotEqual(first['comparison_group'], old['comparison_group'])
        self.assertNotEqual(first['comparison_group'], second['comparison_group'])
        peer = deepcopy(first)
        peer['id'] = 'same-run-peer'
        self.assertEqual(visible_catalog(first, [first, peer]),
                         ['run-a', 'same-run-peer'])
        self.assertEqual(first['actual_source_id'], 'old-local')
        self.assertEqual(first['payload'], old['payload'])
        self.assertEqual(old, before)
        first['payload']['mask'].append([6, 7])
        self.assertEqual(old, before)
        with self.assertRaisesRegex(ValueError, 'unsupported saved session field'):
            visible_catalog(old, [old])
        invalid = deepcopy(first)
        invalid['session']['obsolete_notes'] = []
        with self.assertRaisesRegex(ValueError, 'unsupported saved session field'):
            visible_catalog(invalid, [invalid])


if __name__ == '__main__':
    unittest.main()
