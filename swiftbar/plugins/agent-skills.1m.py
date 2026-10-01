#!/usr/bin/env python3
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
    'partial': '未対応の記録・読取エラーあり', 'lagging': '取り込み中',
    'awaiting_line': '書き込み完了待ち', 'missing': '保存元未発見', 'unconfigured': '未設定',
}
OUTCOMES = {
    'reported_passed': '検証済', 'reported_failed': '検証失敗',
    'unverified': '未検証', 'no_end': '終了記録なし', 'legacy': '旧形式',
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


def render(analysis):
    collection = analysis['collection']
    states = {row['state'] for row in collection.get('runtimes', [])}
    attention = collection['state'] not in {'running', 'legacy_archive'} or bool(
        states - {'up_to_date', 'awaiting_line', 'unconfigured'}
    )
    summary = analysis.get('work_summary')
    title = f"Skillログ {summary['turns_with_skills']:,}" if summary else 'Skillログ'
    notice = ' · 未対応の記録または収集状態を確認' if attention else ''
    print(f"{title}{' !' if attention else ''}| sfimage=brain.head.profile tooltip=直近{DAYS}日のskill利用作業数{notice}")
    print('---')
    if attention:
        print('注意: 未対応の記録または収集状態を確認')
    if summary:
        source = '通常の保存ログ' if analysis['source'] == 'native' else '旧hookの保存ログ'
        print(f'直近{DAYS}日 · {source}')
        print(f"skill利用の作業: {summary['turns_with_skills']:,}件")
        print(f"最終観測: {timestamp(analysis['coverage']['latest_event_at'])}")
        print('作業中の検証')
        for outcome, label in OUTCOMES.items():
            print(f"--{label}: {summary['outcomes'].get(outcome, 0):,}件")
        print('agent別の利用作業')
        for agent, count in sorted(summary['by_agent'].items()):
            print(f"--{text(AGENTS.get(agent, agent))}: {count:,}件")
        print('利用の多いskill（併用はそれぞれに計上）')
        for row in summary['top_skills']:
            print(f"--{text(row['skill'])}: {row['turns']:,}作業")
        print('確認する作業記録（失敗・結果未確認を優先）')
        candidates = analysis.get('review_candidates', [])
        if not candidates:
            print('--期間内の候補なし')
        for row in candidates[:3]:
            result = OUTCOMES[row['work_verification']]
            if 'verification_result_unconfirmed' in row['review_reasons']:
                result += '・検証結果未確認'
            skills = ', '.join(s['name'] for s in row['skills'])
            print(f"--{timestamp(row['started_at'])} {text(AGENTS.get(row['agent'], row['agent']))} · {text(skills)} · {result}")
        if ANALYZER.is_file():
            print(f"レビュー候補の根拠を確認| bash='{ANALYZER}' param1=--days param2={DAYS} param3=--limit param4=3 terminal=true")
    else:
        print('利用解析を取得できません。利用件数は未確認です。')
    if REPORTER.is_file():
        print('---')
        for page, label in [('usage', '利用履歴を開く'), ('evals', '比較評価の結果を開く'), ('skills', 'スキルの配置・採否を開く')]:
            print(f"{label}| bash='{REPORTER}' param1=--open param2=--page param3={page} param4=--days param5={DAYS} terminal=false")
    print('---')
    print('収集と記録の不足')
    print(f"--収集: {STATES.get(collection['state'], text(collection['state']))}")
    print(f"--最終収集: {timestamp(collection.get('last_success'))}")
    for row in collection.get('runtimes', []):
        print(f"--{text(AGENTS.get(row['runtime'], row['runtime']))}: {STATES.get(row['state'], text(row['state']))}")
        for code, count in row.get('issues', {}).items():
            print(f"----{text(ISSUES.get(code, code))}: {count:,}件")
        for code, count in row.get('limitations', {}).items():
            print(f"----解析上の制限 · {text(ISSUES.get(code, code))}: {count:,}件")
    if summary:
        quality = analysis['data_quality']
        print(f"--入力の要確認: {quality['invalid_rows_or_files']:,}件")
        print(f"--解析上の制限（読取エラーとは別）: {quality.get('analysis_limit_rows', 0):,}件")
        print(f"--skill版未記録の読み取り: {quality['read_activations_without_version']:,}件")
        print(f"--検証結果未確認: {quality['unconfirmed_verification_results']:,}件")
    if DOCTOR.is_file():
        print(f"収集の詳細を確認| bash='{DOCTOR}' terminal=true")
    print('更新| refresh=true sfimage=arrow.clockwise')


def main():
    try:
        result = subprocess.run([str(ANALYZER), '--days', str(DAYS), '--limit', '3'],
                                capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise ValueError('analysis failed')
        analysis = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        analysis = {'collection': {'state': 'unavailable', 'runtimes': []}}
    render(analysis)


if __name__ == '__main__':
    main()
