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
            'input_error_counts': {'unsupported_codex_wrapper': 6, 'conflicting_native_identity': 1},
            'coverage': {'latest_event_at': '2026-01-20T12:00:00+00:00'},
            'collection': {'state': state, 'runtimes': [{'runtime': 'codex', 'state': runtime}]},
            'data_quality': {'invalid_rows_or_files': 7, 'read_activations_without_version': 2,
                             'unconfirmed_verification_results': 1},
            'work_summary': {'turns_with_skills': 3,
                             'outcomes': {'reported_passed': 1, 'reported_failed': 1, 'unverified': 1},
                             'by_agent': {'codex': 2, 'pi': 1},
                             'top_skills': [{'skill': 'guide|injected\nline', 'turns': 3}]},
            'review_candidates': [{'id': 'a' * 20, 'started_at': '2026-01-20T12:00:00+00:00', 'agent': 'codex',
                                   'skills': [{'name': 'guide'}], 'work_verification': 'reported_failed',
                                   'review_reasons': ['verification_failed']}],
        }

    def render(self, analysis):
        output = StringIO()
        with patch.object(plugin.pathlib.Path, 'is_file', return_value=True), redirect_stdout(output):
            plugin.render(analysis)
        return output.getvalue()

    def submenu(self, output, title):
        lines = output.splitlines()
        start = next(i for i, line in enumerate(lines) if line.split('|')[0] == title)
        children = []
        for line in lines[start + 1:]:
            if not line.startswith('--') or line == '---':
                break
            children.append(line)
        return '\n'.join(children)

    def test_overview_is_compact_and_actions_reach_their_evidence(self):
        output = self.render(self.analysis())
        self.assertTrue(output.startswith('Skills|'))
        self.assertIn('dropdown=false', output.splitlines()[0])
        self.assertIn('3作業 · 直近30日', output)
        roots = [line for line in output.splitlines()[2:] if not line.startswith('--')]
        self.assertLessEqual(len(roots), 12)
        self.assertLess(output.index('収集は稼働中'), output.index('利用の内訳'))
        breakdown = self.submenu(output, '利用の内訳')
        self.assertIn('検証成功の記録あり: 1作業', breakdown)
        self.assertIn('検証失敗の記録あり: 1作業', breakdown)
        self.assertIn('検証結果は未確認: 1作業', breakdown)
        self.assertNotIn('旧形式の記録: 0', breakdown)
        self.assertIn('--2作業  Codex', breakdown)
        self.assertIn('--3作業  guide／injected line| length=48 symbolize=false', breakdown)
        reviews = self.submenu(output, 'レビューと評価ケース')
        self.assertIn('----guide| length=48', reviews)
        self.assertIn('param3=--review-template param4=' + 'a' * 20, reviews)
        self.assertNotIn('guide', next(line for line in reviews.splitlines() if ' · Codex · ' in line))
        for page in ('usage', 'evals', 'skills'):
            self.assertIn('param2=--page param3=' + page, output)
        self.assertNotIn('成功率', output)

    def test_saved_gaps_are_scoped_and_do_not_raise_live_warnings(self):
        analysis = self.analysis()
        runtime = analysis['collection']['runtimes'][0]
        runtime.update(issues={'unsupported_codex_wrapper': 6},
                       limitations={'unsupported_shell_syntax': 8, 'branch_origin_unverified': 2})
        analysis['data_quality']['analysis_limit_rows'] = 10
        output = self.render(analysis)
        self.assertTrue(output.startswith('Skills|'))
        quality = self.submenu(output, '記録の信頼性 · 不足あり')
        window, saved = quality.split('--保存ログ全体の解析範囲')
        self.assertIn('--直近30日の観測', window)
        self.assertIn('版情報のない読み込み: 2件', window)
        self.assertIn('矛盾する観測（集計から除外）: 1件', window)
        self.assertNotIn('旧Codexラッパー', window)
        self.assertIn('6件  内部の実行記録がない旧Codexラッパー', saved)
        self.assertIn('8件  シェル構文の解析対象外', saved)
        self.assertNotIn('版情報のない読み込み', saved)
        self.assertNotIn('入力の要確認: 7件', quality)  # This total mixes both scopes.

    def test_case_proposal_action_and_preparation_failure_do_not_hide_usage(self):
        analysis = self.analysis()
        analysis['evaluation_candidates'] = [{'id': 'b' * 20, 'skill': 'guide', 'label': '通常の利用記録'}]
        analysis['evaluation_candidate_count'] = 8
        analysis['case_preparation'] = {'state': 'failed'}
        output = self.render(analysis)
        self.assertIn('3作業 · 直近30日', output)
        menu = self.submenu(output, 'レビューと評価ケース')
        self.assertIn('評価ケース候補 · 8組', menu)
        self.assertIn('候補の保存に失敗', menu)
        self.assertIn('param3=--case-proposal param4=' + 'b' * 20, menu)
        self.assertIn('原因・既存ケースとの重複は未確認', menu)

    def test_collection_failures_remain_visible_with_actionable_details(self):
        for state, runtime in [('running', 'partial'), ('stopped', 'up_to_date'),
                               ('running', 'lagging'), ('running', 'missing')]:
            with self.subTest(state=state, runtime=runtime):
                analysis = self.analysis(state, runtime)
                analysis['collection']['runtimes'][0].update(file_errors=2, unread_bytes=512)
                output = self.render(analysis)
                self.assertTrue(output.startswith('Skills !|'))
                status = self.submenu(output, '収集に要確認')
                self.assertIn('読取失敗: 2 ファイル', status)
                self.assertIn('未読: 512 bytes', status)
                self.assertIn('収集の詳細を開く', status)

    def test_legacy_is_not_presented_as_confirmed_native_usage(self):
        analysis = self.analysis(state='legacy_archive')
        analysis['source'] = 'legacy'
        analysis['collection']['runtimes'] = []
        output = self.render(analysis)
        self.assertIn('旧hookが記録したスキル利用', output)
        self.assertIn('旧ログを表示中', output)
        self.assertIn('読取対象の旧ログの解析範囲', output)
        self.assertNotIn('保存ログ全体', output)
        self.assertNotIn('読み込みを確認できた作業', output)

    def test_empty_confirmed_analysis_is_distinct_from_unavailable_analysis(self):
        analysis = self.analysis()
        analysis['work_summary'] = {'turns_with_skills': 0, 'outcomes': {}, 'by_agent': {}, 'top_skills': []}
        analysis['review_candidates'] = []
        output = self.render(analysis)
        self.assertTrue(output.startswith('Skills|'))
        self.assertIn('0作業 · 直近30日', output)
        self.assertIn('期間内の候補なし', output)
        for failure in [OSError(), subprocess.TimeoutExpired('analyze', 15), None]:
            with self.subTest(failure=failure):
                result = subprocess.CompletedProcess([], 1, '{}')
                output = StringIO()
                with patch.object(plugin.subprocess, 'run', side_effect=failure, return_value=result), redirect_stdout(output):
                    plugin.main()
                self.assertTrue(output.getvalue().startswith('Skills !|'))
                self.assertIn('利用件数は未確認', output.getvalue())
                self.assertNotIn('0作業', output.getvalue())
                self.assertNotIn('旧ログの解析範囲', output.getvalue())
