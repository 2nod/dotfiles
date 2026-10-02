#!/usr/bin/env python3
# <xbar.title>Skill usage</xbar.title>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
"""Show saved usage analysis and open its evidence; never run evaluations."""
from __future__ import annotations

from datetime import datetime
import json
import pathlib
import subprocess

BIN = pathlib.Path.home() / '.local/bin'
ANALYZER = BIN / 'agent-observability-analyze-usage'
REPORTER = BIN / 'agent-observability-report'
DOCTOR = BIN / 'agent-observability-doctor'
DAYS = 30
AGENTS = {'codex': 'Codex', 'claude-code': 'Claude Code', 'pi': 'Pi'}
STATES = {
    'running': '稼働中', 'stopped': '停止の疑い', 'not_started': '未開始',
    'unreadable': '読み取り不可', 'unavailable': '解析を取得できません',
    'legacy_archive': '旧ログを参照', 'up_to_date': '取り込み済み',
    'partial': 'ファイルの読取エラー・欠落あり', 'lagging': '取り込み中',
    'awaiting_line': '書き込み完了待ち', 'missing': '保存元未発見', 'unconfigured': '未設定',
}
OUTCOMES = {
    'reported_passed': '検証成功の記録あり', 'reported_failed': '検証失敗の記録あり',
    'unverified': '検証結果は未確認', 'no_end': '終了記録なし', 'legacy': '旧形式の記録',
}
ISSUES = {
    'unsupported_codex_wrapper': '内部の実行記録がない旧Codexラッパー',
    'unsupported_codex_item': '未対応のCodex記録形式',
    'unsupported_shell_syntax': 'シェル構文の解析対象外',
    'branch_origin_unverified': '分岐履歴の重複を検証できず集計から除外',
    'oversized_record_skipped': '巨大な活動記録を読み飛ばし',
    'invalid_json': '不正なJSON',
}


def text(value):
    return str(value).replace('|', '／').replace('\n', ' ').replace('\r', ' ')


def timestamp(value):
    if not value:
        return '未記録'
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone().strftime('%m/%d %H:%M')


def report_action(label, page, depth=0):
    if REPORTER.is_file():
        print(f"{'--' * depth}{label}| bash='{REPORTER}' param1=--open param2=--page param3={page} param4=--days param5={DAYS} terminal=false sfimage=arrow.up.right.square")


def render(analysis):
    collection = analysis['collection']
    runtimes = collection.get('runtimes', [])
    attention = collection['state'] not in {'running', 'legacy_archive'} or any(
        row['state'] not in {'up_to_date', 'awaiting_line', 'unconfigured'} for row in runtimes
    )
    summary = analysis.get('work_summary')
    quality = analysis.get('data_quality', {})
    incomplete = any(quality.get(key, 0) for key in (
        'invalid_rows_or_files', 'analysis_limit_rows', 'read_activations_without_version',
        'unconfirmed_verification_results',
    )) or any(row.get('issues') or row.get('limitations') for row in runtimes)
    native = analysis.get('source') == 'native'
    icon = 'exclamationmark.triangle' if attention else 'brain.head.profile'
    print(f"Skills{' !' if attention else ''}| sfimage={icon} dropdown=false tooltip=スキル利用の確認 · 直近{DAYS}日")
    print('---')
    if summary:
        print(f"{summary['turns_with_skills']:,}作業 · 直近{DAYS}日| size=18")
        print('スキルの読み込みを確認できた作業| size=11' if native else '旧hookが記録したスキル利用| size=11')
    else:
        print('利用件数は未確認| size=18')
        print('利用解析を取得できません| size=11')
    status = ('収集に要確認' if attention else
              '旧ログを表示中' if collection['state'] == 'legacy_archive' else '収集は稼働中')
    status_icon = 'exclamationmark.triangle' if attention else 'clock.arrow.circlepath'
    print(f"{status}| sfimage={status_icon}")
    print(f"--状態: {STATES.get(collection['state'], text(collection['state']))}")
    print(f"--最終収集: {timestamp(collection.get('last_success'))}")
    for row in runtimes:
        print(f"--{text(AGENTS.get(row['runtime'], row['runtime']))}: {STATES.get(row['state'], text(row['state']))}")
        for key, label, unit in [('unread_bytes', '未読', 'bytes'), ('file_errors', '読取失敗', 'ファイル'),
                                 ('missing_files', '保存元の欠落', 'ファイル'), ('replaying_files', '再解析中', 'ファイル')]:
            if row.get(key):
                print(f"----{label}: {row[key]:,} {unit}")
    if DOCTOR.is_file():
        print(f"--収集の詳細を開く| bash='{DOCTOR}' terminal=true")
    print('---')
    if summary:
        print('利用の内訳| sfimage=chart.bar')
        print(f"--直近{DAYS}日 · 作業単位")
        print(f"--最終観測: {timestamp(analysis['coverage']['latest_event_at'])}")
        print('-----')
        for agent, count in sorted(summary['by_agent'].items(), key=lambda pair: (-pair[1], pair[0])):
            print(f"--{count:,}作業  {text(AGENTS.get(agent, agent))}")
        print('-----')
        print('--よく使ったスキル（併用はそれぞれに計上）')
        for row in summary['top_skills']:
            print(f"--{row['turns']:,}作業  {text(row['skill'])}| length=48 symbolize=false")
        print('-----')
        print('--作業内の検証記録（スキルの評価ではありません）')
        for outcome, label in OUTCOMES.items():
            count = summary['outcomes'].get(outcome, 0)
            if count:
                print(f"--{label}: {count:,}作業")
        candidates = analysis.get('review_candidates', [])[:3]
        print('レビューと評価ケース| sfimage=text.magnifyingglass')
        proposals = analysis.get('evaluation_candidates', [])[:4]
        print(f"--実ログからの評価ケース候補 · {analysis.get('evaluation_candidate_count', len(proposals))}組")
        reviews = analysis.get('case_review_summary', {})
        print(f"--終了済み · 結果・設計あり: {reviews.get('reviewed', 0)}作業 / 未確認: {reviews.get('pending', 0)}作業")
        if reviews.get('needs_review'):
            print(f"--根拠・設計の再確認: {reviews['needs_review']}作業")
        print('--未確認の作業は原因・ケース重複の確認が必要')
        if analysis.get('case_preparation', {}).get('state') == 'failed':
            print('--候補の保存に失敗（現在の候補は下に表示）')
        if analysis.get('case_catalog_errors'):
            print('--既存ケースを一部読み取れません')
        for proposal in proposals:
            proposal_id = proposal['id']
            if ANALYZER.is_file() and len(proposal_id) == 20 and all(c in '0123456789abcdef' for c in proposal_id):
                print(f"--{text(proposal['skill'])} · {text(proposal['label'])}| length=48 symbolize=false bash='{ANALYZER}' param1=--days param2={DAYS} param3=--case-proposal param4={proposal_id} terminal=true")
        if not proposals:
            print('--候補なし（終了記録のある共有スキル利用が対象）')
        if ANALYZER.is_file():
            print(f"--すべての候補を開く| bash='{ANALYZER}' param1=--days param2={DAYS} param3=--limit param4=1000 terminal=true")
        print('-----')
        print(f'--元の作業を確認 · {len(candidates)}件表示')
        print(f'--直近{DAYS}日 · 検証失敗・結果未確認を優先')
        if not candidates:
            print('--期間内の候補なし')
        for row in candidates:
            result = OUTCOMES[row['work_verification']]
            print(f"--{timestamp(row['started_at'])} · {text(AGENTS.get(row['agent'], row['agent']))} · {result}")
            if 'verification_result_unconfirmed' in row['review_reasons']:
                print('----結果を確定できない検証も含みます')
            for skill in row['skills']:
                print(f"----{text(skill['name'])}| length=48 symbolize=false")
            review = row.get('case_review', {})
            if review.get('state') == 'reviewed':
                print(f"----レビュー結果: {text(review['result']['summary'])}| length=52 symbolize=false")
            if ANALYZER.is_file():
                # IDs are generated by the analyzer, never transcript text.
                candidate_id = row.get('id', '')
                if len(candidate_id) == 20 and all(c in '0123456789abcdef' for c in candidate_id):
                    print(f"----この作業の根拠を開く| bash='{ANALYZER}' param1=--days param2={DAYS} param3=--review-template param4={candidate_id} terminal=true")
        report_action('利用履歴を開く', 'usage')
    print('---')
    coverage_label = '記録の信頼性 · 不足あり' if incomplete else '記録の信頼性'
    print(f'{coverage_label}| sfimage=info.circle')
    print('--利用件数は確認できた記録の集計です')
    print('--記録の不足はスキルの未使用を意味しません')
    if summary:
        print('-----')
        print(f'--直近{DAYS}日の観測')
        print(f"--版情報のない読み込み: {quality.get('read_activations_without_version', 0):,}件")
        print(f"--結果を確定できない検証: {quality.get('unconfirmed_verification_results', 0):,}件")
        conflicts = analysis.get('input_error_counts', {}).get('conflicting_native_identity', 0)
        if native and conflicts:
            print(f'--矛盾する観測（集計から除外）: {conflicts:,}件')
    print('-----')
    scope = ('保存ログ全体の解析範囲' if native else
             '読取対象の旧ログの解析範囲' if analysis.get('source') == 'legacy' else '解析範囲は未確認')
    print(f'--{scope}')
    for row in runtimes:
        if row.get('issues') or row.get('limitations'):
            print(f"--{text(AGENTS.get(row['runtime'], row['runtime']))}")
        for code, count in {**row.get('issues', {}), **row.get('limitations', {})}.items():
            print(f"----{count:,}件  {text(ISSUES.get(code, code))}| length=52 symbolize=false")
    if not native:
        for code, count in analysis.get('input_error_counts', {}).items():
            print(f"--{count:,}件  {text(ISSUES.get(code, code))}| length=52 symbolize=false")
    if ANALYZER.is_file():
        print(f"--診断の全項目を開く| bash='{ANALYZER}' param1=--days param2={DAYS} param3=--limit param4=3 terminal=true")
    if REPORTER.is_file():
        print('その他のレポート| sfimage=doc.text')
        report_action('スキルの配置・採否', 'skills', 1)
        report_action('比較評価の結果', 'evals', 1)
    print('更新| refresh=true sfimage=arrow.clockwise')


def main():
    try:
        result = subprocess.run([str(ANALYZER), '--days', str(DAYS), '--limit', '4', '--prepare-cases'],
                                capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise ValueError('analysis failed')
        analysis = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        analysis = {'collection': {'state': 'unavailable', 'runtimes': []}}
    render(analysis)


if __name__ == '__main__':
    main()
