"""SwiftBar uses analysis counts and keeps collection health separate."""
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    'swiftbar_skills', Path(__file__).resolve().parents[1] / 'swiftbar/plugins/agent-skills.1m.py'
)
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


class SwiftBarTest(unittest.TestCase):
    def analysis(self, state='running', runtime='up_to_date'):
        return {
            'source': 'native',
            'coverage': {'latest_event_at': '2026-01-20T12:00:00+00:00'},
            'collection': {'state': state, 'runtimes': [{'runtime': 'codex', 'state': runtime}]},
            'data_quality': {'invalid_rows_or_files': 7, 'read_activations_without_version': 2,
                             'unconfirmed_verification_results': 1},
            'work_summary': {'turns_with_skills': 3,
                             'outcomes': {'reported_passed': 1, 'reported_failed': 1, 'unverified': 1},
                             'by_agent': {'codex': 2, 'pi': 1},
                             'top_skills': [{'skill': 'guide|injected\nline', 'turns': 3}]},
            'review_candidates': [{'started_at': '2026-01-20T12:00:00+00:00', 'agent': 'codex',
                                   'skills': [{'name': 'guide'}], 'work_verification': 'reported_failed',
                                   'review_reasons': ['verification_failed']}],
        }

    def render(self, analysis):
        output = StringIO()
        with patch.object(plugin.pathlib.Path, 'is_file', return_value=True), redirect_stdout(output):
            plugin.render(analysis)
        return output.getvalue()

    def test_analysis_drives_metrics_candidates_and_page_actions(self):
        output = self.render(self.analysis())
        self.assertTrue(output.startswith('Skillログ 3|'))
        self.assertIn('skill利用の作業: 3件', output)
        for label in ('検証済', '検証失敗', '未検証'):
            self.assertIn(f'--{label}: 1件', output)
        self.assertIn('--Codex: 2件', output)
        self.assertIn('--guide／injected line: 3作業', output)
        self.assertIn('guide · 検証失敗', output)
        self.assertLess(output.index('skill利用の作業'), output.index('収集と記録の不足'))
        for page in ('usage', 'evals', 'skills'):
            self.assertIn('param2=--page param3=' + page, output)
        self.assertIn('--入力の要確認: 7件', output)
        self.assertNotIn('成功率', output)

    def test_attention_comes_from_collection_not_historical_verification_failures(self):
        for state, runtime in [('running', 'partial'), ('stopped', 'up_to_date')]:
            with self.subTest(state=state, runtime=runtime):
                self.assertTrue(self.render(self.analysis(state, runtime)).startswith('Skillログ 3 !|'))

    def test_limits_remain_visible_without_claiming_a_read_error(self):
        analysis = self.analysis()
        row = analysis['collection']['runtimes'][0]
        row['limitations'] = {'unsupported_shell_syntax': 8, 'branch_origin_unverified': 2}
        analysis['data_quality']['analysis_limit_rows'] = 10
        output = self.render(analysis)
        self.assertTrue(output.startswith('Skillログ 3|'))
        self.assertIn('シェル構文の解析対象外: 8件', output)
        self.assertIn('解析上の制限（読取エラーとは別）: 10件', output)
        row['issues'] = {'unsupported_codex_wrapper': 3}
        output = self.render(analysis)
        self.assertTrue(output.startswith('Skillログ 3|'))
        self.assertIn('内部の実行記録がない旧Codexラッパー: 3件', output)
        self.assertIn('保存ログ全体の解析不足', output)
        self.assertIn('読み込みを確認できたskill利用作業数', output)
        row['state'] = 'partial'
        output = self.render(analysis)
        self.assertTrue(output.startswith('Skillログ 3 !|'))
        self.assertIn('注意: 収集状態を確認', output)

    def test_empty_confirmed_analysis_is_distinct_from_unavailable_analysis(self):
        analysis = self.analysis()
        analysis['work_summary'] = {'turns_with_skills': 0, 'outcomes': {}, 'by_agent': {}, 'top_skills': []}
        analysis['review_candidates'] = []
        output = self.render(analysis)
        self.assertTrue(output.startswith('Skillログ 0|'))
        self.assertIn('期間内の候補なし', output)
        for failure in [OSError(), subprocess.TimeoutExpired('analyze', 15), None]:
            with self.subTest(failure=failure):
                result = subprocess.CompletedProcess([], 1, '{}')
                output = StringIO()
                with patch.object(plugin.subprocess, 'run', side_effect=failure, return_value=result), redirect_stdout(output):
                    plugin.main()
                self.assertTrue(output.getvalue().startswith('Skillログ !|'))
                self.assertIn('利用件数は未確認', output.getvalue())
                self.assertNotIn('Skillログ 0', output.getvalue())
